#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db
.venv/bin/python manage.py migrate --check
exec .venv/bin/python manage.py runserver "0.0.0.0:${PORT:-8000}"
