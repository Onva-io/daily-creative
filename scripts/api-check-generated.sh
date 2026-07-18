#!/usr/bin/env bash
# Fail if committed generated Swift client differs from regeneration of openapi.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/api/generated/ios"
FRESH="$(mktemp -d "${TMPDIR:-/tmp}/dailysketch-openapi-check.XXXXXX")"

cleanup() {
  rm -rf "${FRESH}"
}
trap cleanup EXIT

if [[ ! -d "${OUT}" ]]; then
  echo "Missing generated client at ${OUT}. Run make api-generate-ios." >&2
  exit 1
fi

API_GENERATED_OUT="${FRESH}/ios" bash "${ROOT}/scripts/api-generate-ios.sh"

if ! diff -ru "${OUT}" "${FRESH}/ios"; then
  echo "Generated OpenAPI client is stale. Run make api-generate-ios and commit." >&2
  exit 1
fi

echo "Generated OpenAPI client is up to date."
