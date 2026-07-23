#!/bin/sh
# Production start: migrate, then bind to Railway's PORT when set (else 8000).
set -eu

echo "[start] Applying database migrations..."
alembic upgrade head

echo "[start] Starting API on :${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
