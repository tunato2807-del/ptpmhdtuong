#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir .local/pip-cache -r requirements.txt
docker compose up -d --wait db
.venv/bin/python manage.py migrate --noinput
if [ "${LOAD_DEMO_DATA:-1}" = "1" ]; then
  .venv/bin/python manage.py seed_demo
fi
.venv/bin/python manage.py check
.venv/bin/python manage.py collectstatic --noinput
