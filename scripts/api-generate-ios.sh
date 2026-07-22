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

# Pin the generator JAR via openapitools.json (must be committed; CLI defaults differ across machines).
npx --yes @openapitools/openapi-generator-cli@2.15.3 generate \
  --openapitools "${ROOT}/openapitools.json" \
  -i "${SPEC}" \
  -g swift5 \
  -o "${TMP}" \
  --additional-properties=projectName=DailyCreativeAPI,responseAs=AsyncAwait,library=urlsession,hideGenerationTimestamp=true \
  --skip-validate-spec

rm -rf "${OUT}"
mkdir -p "${OUT}"

# swift5 generator emits DailyCreativeAPI/Classes plus Package.swift
if [[ -d "${TMP}/DailyCreativeAPI" ]]; then
  cp -R "${TMP}/DailyCreativeAPI" "${OUT}/DailyCreativeAPI"
fi
if [[ -f "${TMP}/Package.swift" ]]; then
  cp "${TMP}/Package.swift" "${OUT}/Package.swift"
fi
if [[ -d "${TMP}/.openapi-generator" ]]; then
  cp -R "${TMP}/.openapi-generator" "${OUT}/.openapi-generator"
fi

if [[ ! -d "${OUT}/DailyCreativeAPI" ]]; then
  echo "OpenAPI generator did not produce DailyCreativeAPI sources." >&2
  exit 1
fi

# openapi-generator emits `extension String: CodingKey`, which Swift 6 warns about as a
# retroactive conformance. Mark it explicitly so builds stay clean across regenerations.
EXTENSIONS="${OUT}/DailyCreativeAPI/Classes/OpenAPIs/Extensions.swift"
if [[ -f "${EXTENSIONS}" ]]; then
  perl -i -pe 's/extension String: CodingKey/extension String: \@retroactive CodingKey/g' "${EXTENSIONS}"
fi

# DateFormatter is @unchecked Sendable; Swift 6 requires subclasses to restate that.
FORMATTER="${OUT}/DailyCreativeAPI/Classes/OpenAPIs/OpenISO8601DateFormatter.swift"
if [[ -f "${FORMATTER}" ]]; then
  perl -i -pe 's/public class OpenISO8601DateFormatter: DateFormatter \{/public class OpenISO8601DateFormatter: DateFormatter, \@unchecked Sendable \{/g' "${FORMATTER}"
fi

# URLSession dataTask completions are @Sendable; mark request builders so capturing
# self in those closures is valid under Swift 6 strict concurrency.
APIS="${OUT}/DailyCreativeAPI/Classes/OpenAPIs/APIs.swift"
if [[ -f "${APIS}" ]]; then
  perl -i -pe 's/open class RequestBuilder<T> \{/open class RequestBuilder<T>: \@unchecked Sendable \{/g' "${APIS}"
fi
URLSESSION="${OUT}/DailyCreativeAPI/Classes/OpenAPIs/URLSessionImplementations.swift"
if [[ -f "${URLSESSION}" ]]; then
  perl -i -pe 's/open class URLSessionRequestBuilder<T>: RequestBuilder<T> \{/open class URLSessionRequestBuilder<T>: RequestBuilder<T>, \@unchecked Sendable \{/g' "${URLSESSION}"
  perl -i -pe 's/open class URLSessionDecodableRequestBuilder<T: Decodable>: URLSessionRequestBuilder<T> \{/open class URLSessionDecodableRequestBuilder<T: Decodable>: URLSessionRequestBuilder<T>, \@unchecked Sendable \{/g' "${URLSESSION}"
fi

echo "Generated Swift client at ${OUT}"
