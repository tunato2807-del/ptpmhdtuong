"""Maintainer: run after committing source, then commit just the manifest.
The updater always reads immutable files from the recorded source commit.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ref = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref], cwd=ROOT, text=True).splitlines()
files = []
for name in paths:
    if name == 'scripts/update_manifest.json':
        continue
    if name in {'manage.py', 'requirements.txt', 'requirements-dev.txt', 'README.md', '.env.example'} or name.startswith(('config/', 'salon/', 'templates/', 'static/', 'scripts/')):
        data = subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
        files.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest()})
(ROOT / 'scripts/update_manifest.json').write_text(json.dumps({'ref': ref, 'files': files}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Manifest:', ref, len(files), 'files')
