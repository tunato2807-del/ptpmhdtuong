#!/usr/bin/env bash
# Cloud fallback when Docker's build network cannot resolve public package hosts.
# Host Python and target image must both use Linux / Python 3.12 / same CPU arch.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .build-wheels .local/docker
export DOCKER_CONFIG="${DOCKER_CONFIG:-$PWD/.local/docker}"
.venv/bin/python -m pip download --only-binary=:all: --dest .build-wheels -r requirements.txt
docker compose build --build-arg PIP_NO_INDEX=1 web
