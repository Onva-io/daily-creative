#!/usr/bin/env bash
# Local Compose entrypoint: sync deps, migrate, then serve with reload.
set -euo pipefail

cd /app

echo "[dev] Syncing Python dependencies..."
uv pip install --system -e ".[dev]"

echo "[dev] Applying database migrations..."
alembic upgrade head

if [[ $# -gt 0 ]]; then
  echo "[dev] Running: $*"
  exec "$@"
fi

echo "[dev] Starting API with reload on :8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
