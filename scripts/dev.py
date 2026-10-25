"""Cross-platform local development with an existing PostgreSQL server.

Windows: python scripts/dev.py setup | start | check
Linux/macOS: python3 scripts/dev.py setup | start | check
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def run(*args):
    subprocess.run([str(PYTHON), *map(str, args)], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description='Chạy GENTLEMAN với PostgreSQL cài sẵn trên máy.')
    parser.add_argument('command', choices=['setup', 'start', 'check'])
    parser.add_argument('--no-demo', action='store_true', help='Không nạp dữ liệu mẫu khi setup.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8000')))
    args = parser.parse_args()
    if args.command == 'setup':
        if not PYTHON.exists():
            subprocess.run([sys.executable, '-m', 'venv', str(ROOT / '.venv')], check=True)
        run('-m', 'pip', 'install', '-r', 'requirements.txt')
        if not (ROOT / '.env').exists():
            (ROOT / '.env').write_bytes((ROOT / '.env.example').read_bytes())
            print('Đã tạo .env. Điền mật khẩu PostgreSQL và tạo database gentleman trong pgAdmin, rồi chạy lại setup.', flush=True)
            return 1
    elif not PYTHON.exists():
        parser.error('Chưa có .venv. Hãy chạy: python scripts/dev.py setup')
    run('manage.py', 'check_database')
    if args.command == 'setup':
        run('manage.py', 'migrate', '--noinput')
        if not args.no_demo and os.getenv('LOAD_DEMO_DATA', '1') == '1':
            run('manage.py', 'seed_demo')
        run('manage.py', 'check')
        run('manage.py', 'collectstatic', '--noinput')
        print('Sẵn sàng. Chạy: python scripts/dev.py start', flush=True)
    elif args.command == 'start':
        run('manage.py', 'migrate', '--check')
        run('manage.py', 'runserver', f'{args.host}:{args.port}')
    else:
        run('manage.py', 'check')
        run('manage.py', 'makemigrations', '--check', '--dry-run')
        run('manage.py', 'collectstatic', '--noinput')
        run('manage.py', 'test', 'salon.tests', '--noinput')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        print('Đã dừng tại lệnh bị lỗi. Kiểm tra thông báo phía trên trước khi chạy tiếp.', file=sys.stderr)
        sys.exit(error.returncode or 1)
    except KeyboardInterrupt:
        sys.exit(0)
