#!/bin/sh
# Production start: migrate, then bind to Railway's PORT when set (else 8000).
set -eu

echo "[start] Applying database migrations..."
alembic upgrade head

# Non-fatal: an API that boots without policies is degraded, but one that never boots
# is worse. Failures log here and page through ALERT_WEBHOOK_URL.
echo "[start] Bootstrapping policy documents..."
if ! python -m app.seeds.policies --bootstrap; then
  echo "[start] WARNING: policy bootstrap failed; consent gating may be inactive." >&2
fi

echo "[start] Starting API on :${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
