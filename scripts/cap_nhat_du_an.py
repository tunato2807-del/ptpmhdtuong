"""Copy a complete, verified source revision from the project's own GitHub.

Stdlib only; Python 3.12–3.14. Keeps .env, .venv and PostgreSQL untouched.
Run after stopping Django: python scripts/cap_nhat_du_an.py
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

RAW = 'https://raw.githubusercontent.com/tunato2807-del/ptpmhdtuong/'
PREFIXES = ('config/', 'salon/', 'templates/', 'static/', 'scripts/', 'docs/')
ROOT_FILES = {'manage.py', 'requirements.txt', 'requirements-dev.txt', 'README.md', '.env.example'}


def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Gentleman-Source-Updater/1'}), timeout=30) as response:
                data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError('File vuot gioi han 8 MB.')
                return data
        except (URLError, TimeoutError):
            if attempt == 2:
                raise


def validate_manifest(manifest):
    ref = manifest.get('ref', '')
    files = manifest.get('files', [])
    if not re.fullmatch(r'[0-9a-f]{40}', ref) or not 1 <= len(files) <= 400:
        raise ValueError('Manifest khong hop le.')
    seen = set()
    for item in files:
        name = item['path']
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                or str(path) != name or name in seen
                or not (name in ROOT_FILES or name.startswith(PREFIXES))
                or any(part in ('.env', '.venv', '.local', '__pycache__', '.git') for part in path.parts)
                or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
            raise ValueError('Duong dan/hash khong hop le: ' + name)
        seen.add(name)
    return ref, files


def apply_files(root, stage, names, backup):
    """Back up before any replacement; undo applied files if a write fails."""
    existed = {}
    for name in names:
        target = root / name
        if target.is_symlink() or target.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError('Khong cap nhat qua symlink: ' + name)
        existed[name] = target.exists()
        if target.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    applied = []
    try:
        for name in names:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.copymode(target, stage / name)
            os.replace(stage / name, target)
            applied.append(name)
    except BaseException:
        for name in reversed(applied):
            if existed[name]:
                shutil.copy2(backup / name, root / name)
            else:
                (root / name).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='Dong bo du file ma nguon tu GitHub, co sao luu.')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--check-only', action='store_true', help='Chi liet ke file thieu/khac, khong thay the.')
    args = parser.parse_args()
    locations = [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, Path.cwd()]
    root = args.project.resolve() if args.project else next((p for p in locations if (p / 'manage.py').is_file()), None)
    if root is None or not (root / 'manage.py').is_file():
        raise ValueError('Chua tim thay manage.py. Dung --project DUONG_DAN_DU_AN.')
    manifest = json.loads(fetch(RAW + 'main/scripts/update_manifest.json'))
    ref, files = validate_manifest(manifest)
    changed = []
    for item in files:
        target = root / item['path']
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
            changed.append(item)
    print('Phien ban:', ref[:12], '| File can cap nhat:', len(changed), flush=True)
    if args.check_only:
        for item in changed:
            print(item['path'])
        return 1 if changed else 0
    if not changed:
        print('Ma nguon da du va dung phien ban. Khong thay doi file nao.')
        return 0
    folder = root / '.local' / ('cap-nhat-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    stage, backup = folder / 'tai-ve', folder / 'sao-luu'

    def prepare(item):
        name = item['path']
        data = fetch(RAW + ref + '/' + name)
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Sai SHA256: ' + name + '. Chua thay the ma nguon.')
        if name.endswith('.py'):
            compile(data, name, 'exec')
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return name

    # Download and verify EVERY file before changing the existing source.
    with ThreadPoolExecutor(max_workers=6) as pool:
        names = list(pool.map(prepare, changed))
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    apply_files(root, stage, names, backup)
    print('Da cap nhat', len(names), 'file. Ban sao luu:', backup)
    print('Giu nguyen .env, .venv va database. Tiep theo: pip install -r requirements.txt; manage.py check; collectstatic --noinput.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError, URLError) as error:
        print('Khong hoan tat cap nhat:', str(error), file=sys.stderr)
        sys.exit(1)
