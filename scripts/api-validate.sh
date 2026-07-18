#!/usr/bin/env bash
# Validate api/openapi/openapi.yaml against the OpenAPI 3.x schema.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC="${ROOT}/api/openapi/openapi.yaml"

cd "${ROOT}/backend"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python - <<'PY' "${SPEC}"
import sys
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

spec_path = sys.argv[1]
spec, _ = read_from_filename(spec_path)
validate(spec)
print(f"OpenAPI validation passed: {spec_path}")
PY
