#!/usr/bin/env bash
# Generate Swift API client types into api/generated/ios from the OpenAPI contract.
# Optional: API_GENERATED_OUT overrides the output directory.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC="${ROOT}/api/openapi/openapi.yaml"
OUT="${API_GENERATED_OUT:-${ROOT}/api/generated/ios}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/dailysketch-openapi.XXXXXX")"

cleanup() {
  rm -rf "${TMP}"
}
trap cleanup EXIT

npx --yes @openapitools/openapi-generator-cli@2.15.3 generate \
  -i "${SPEC}" \
  -g swift5 \
  -o "${TMP}" \
  --additional-properties=projectName=DailySketchAPI,responseAs=AsyncAwait,library=urlsession,hideGenerationTimestamp=true \
  --skip-validate-spec

rm -rf "${OUT}"
mkdir -p "${OUT}"

# swift5 generator emits DailySketchAPI/Classes plus Package.swift
if [[ -d "${TMP}/DailySketchAPI" ]]; then
  cp -R "${TMP}/DailySketchAPI" "${OUT}/DailySketchAPI"
fi
if [[ -f "${TMP}/Package.swift" ]]; then
  cp "${TMP}/Package.swift" "${OUT}/Package.swift"
fi
if [[ -d "${TMP}/.openapi-generator" ]]; then
  cp -R "${TMP}/.openapi-generator" "${OUT}/.openapi-generator"
fi

if [[ ! -d "${OUT}/DailySketchAPI" ]]; then
  echo "OpenAPI generator did not produce DailySketchAPI sources." >&2
  exit 1
fi

# openapi-generator emits `extension String: CodingKey`, which Swift 6 warns about as a
# retroactive conformance. Mark it explicitly so builds stay clean across regenerations.
EXTENSIONS="${OUT}/DailySketchAPI/Classes/OpenAPIs/Extensions.swift"
if [[ -f "${EXTENSIONS}" ]]; then
  perl -i -pe 's/extension String: CodingKey/extension String: \@retroactive CodingKey/g' "${EXTENSIONS}"
fi

echo "Generated Swift client at ${OUT}"
