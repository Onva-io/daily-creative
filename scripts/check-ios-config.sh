#!/usr/bin/env bash
# Validate that Release iOS xcconfigs have real (non-placeholder) values for
# keys that must never ship to TestFlight / App Store with mock or local config.
#
# Usage:
#   scripts/check-ios-config.sh              # check every Release-* xcconfig
#   scripts/check-ios-config.sh Release-Staging
#   scripts/check-ios-config.sh "$CONFIGURATION"   # from an Xcode build phase
#
# Debug-* configurations are skipped (placeholders are intentional there).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_ROOT="${ROOT}/ios/Config"

REQUIRED_KEYS=(
  API_BASE_URL
  APP_ENVIRONMENT
  DESCOPE_PROJECT_ID
  PRIVACY_URL
  TERMS_URL
  COMMUNITY_GUIDELINES_URL
  SUPPORT_URL
  SUPPORT_EMAIL
)

URL_KEYS=(
  API_BASE_URL
  PRIVACY_URL
  TERMS_URL
  COMMUNITY_GUIDELINES_URL
  SUPPORT_URL
)

# Flatten an xcconfig (and its #include chain) into KEY=VALUE lines.
# Later assignments win. Strips // comments and the /$() URL-escape trick.
resolve_xcconfig() {
  local file="$1"
  local dir
  dir="$(cd "$(dirname "${file}")" && pwd)"
  local base
  base="$(basename "${file}")"
  local resolved="${dir}/${base}"

  if [[ ! -f "${resolved}" ]]; then
    echo "Missing xcconfig: ${resolved}" >&2
    return 1
  fi

  local line include_path include_file key value
  while IFS= read -r line || [[ -n "${line}" ]]; do
    # Strip // comments (xcconfig treats // as comment start).
    line="${line%%//*}"
    # Trim whitespace
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "${line}" ]] && continue

    if [[ "${line}" =~ ^#include[[:space:]]+\"([^\"]+)\" ]]; then
      include_path="${BASH_REMATCH[1]}"
      if [[ "${include_path}" = /* ]]; then
        include_file="${include_path}"
      else
        include_file="${dir}/${include_path}"
      fi
      resolve_xcconfig "${include_file}"
      continue
    fi

    if [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      value="${value#"${value%%[![:space:]]*}"}"
      value="${value%"${value##*[![:space:]]}"}"
      # Xcode xcconfig URL trick: https:/$()/host → https://host
      value="${value//\$()/}"
      printf '%s=%s\n' "${key}" "${value}"
    fi
  done < "${resolved}"
}

lookup_key() {
  local resolved_blob="$1"
  local key="$2"
  # Last assignment wins
  printf '%s\n' "${resolved_blob}" | awk -F= -v k="${key}" '
    $1 == k { v = substr($0, index($0, "=") + 1) }
    END { print v }
  '
}

is_url_key() {
  local key="$1"
  local candidate
  for candidate in "${URL_KEYS[@]}"; do
    if [[ "${candidate}" == "${key}" ]]; then
      return 0
    fi
  done
  return 1
}

validate_file() {
  local file="$1"
  local rel="${file#"${ROOT}/"}"
  local blob
  blob="$(resolve_xcconfig "${file}")"

  local key value failed=0
  for key in "${REQUIRED_KEYS[@]}"; do
    value="$(lookup_key "${blob}" "${key}")"
    if [[ -z "${value}" ]]; then
      echo "error: ${rel}: ${key} is missing or empty" >&2
      failed=1
      continue
    fi
    if [[ "${value}" == *replace-me* ]]; then
      echo "error: ${rel}: ${key} must not use a placeholder (got '${value}')" >&2
      failed=1
      continue
    fi
    if is_url_key "${key}"; then
      if [[ "${value}" == *localhost* || "${value}" == *127.0.0.1* ]]; then
        echo "error: ${rel}: ${key} must not point at localhost (got '${value}')" >&2
        failed=1
        continue
      fi
      if [[ "${value}" == http://* ]]; then
        echo "error: ${rel}: ${key} must use https (got '${value}')" >&2
        failed=1
        continue
      fi
    fi
  done

  if [[ "${failed}" -ne 0 ]]; then
    return 1
  fi
  echo "ok ${rel}"
}

CONFIGURATION_ARG="${1:-}"

if [[ -n "${CONFIGURATION_ARG}" ]]; then
  case "${CONFIGURATION_ARG}" in
    Debug-*)
      echo "Skipping iOS config check for ${CONFIGURATION_ARG} (placeholders allowed)."
      exit 0
      ;;
    Release-*)
      ;;
    *)
      echo "Unknown configuration '${CONFIGURATION_ARG}'. Expected Debug-* or Release-*." >&2
      exit 1
      ;;
  esac
fi

shopt -s nullglob
files=()
if [[ -n "${CONFIGURATION_ARG}" ]]; then
  # Match Sketch (ios/Config/Release-*.xcconfig) and Story (ios/Config/DailyStory/...).
  for candidate in \
    "${CONFIG_ROOT}/${CONFIGURATION_ARG}.xcconfig" \
    "${CONFIG_ROOT}/DailyStory/${CONFIGURATION_ARG}.xcconfig"
  do
    if [[ -f "${candidate}" ]]; then
      files+=("${candidate}")
    fi
  done
  if [[ "${#files[@]}" -eq 0 ]]; then
    echo "No xcconfig found for configuration ${CONFIGURATION_ARG} under ${CONFIG_ROOT}" >&2
    exit 1
  fi
else
  files=(
    "${CONFIG_ROOT}"/Release-*.xcconfig
    "${CONFIG_ROOT}"/DailyStory/Release-*.xcconfig
  )
fi

if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No Release xcconfigs found under ${CONFIG_ROOT}" >&2
  exit 1
fi

echo "== iOS release config =="
failures=0
for file in "${files[@]}"; do
  if ! validate_file "${file}"; then
    failures=1
  fi
done

if [[ "${failures}" -ne 0 ]]; then
  echo "iOS release config check failed. Set real values in Release-* xcconfigs (placeholders and localhost are not allowed)." >&2
  exit 1
fi

echo "iOS release config check passed."
