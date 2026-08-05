#!/usr/bin/env bash
set -euo pipefail

public_origin="${BTSP_PUBLIC_ORIGIN:-https://purchasing-events.us}"
public_origin="${public_origin%/}"
require_cloudflare="${BTSP_REQUIRE_CLOUDFLARE:-true}"
temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/btsp-health.XXXXXX")"
failures=()

cleanup() {
  local status=$?
  trap - EXIT
  rm -rf "$temporary_directory"
  exit "$status"
}
trap cleanup EXIT

request_endpoint() {
  local path="$1"
  local output_file="$2"
  local result
  result="$(curl --silent --show-error --max-time 20 \
    --output "$output_file" \
    --write-out '%{http_code} %{time_total}' \
    "$public_origin$path" || true)"
  local status_code="${result%% *}"
  local elapsed="${result#* }"
  if [[ "$status_code" != 200 ]]; then
    failures+=("$path returned HTTP $status_code")
    printf 'FAIL %-18s HTTP %s\n' "$path" "$status_code"
    return
  fi
  printf 'PASS %-18s HTTP 200 (%ss)\n' "$path" "$elapsed"
}

request_endpoint /api/v1/health "$temporary_directory/health.json"
request_endpoint /api/v1/ready "$temporary_directory/ready.json"
request_endpoint / "$temporary_directory/index.html"

if ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' "$temporary_directory/health.json"; then
  failures+=("health response did not report status=ok")
  echo 'FAIL health response status'
fi
if ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"ready"' "$temporary_directory/ready.json"; then
  failures+=("ready response did not report status=ready")
  echo 'FAIL ready response status'
fi

curl --silent --show-error --max-time 20 --head "$public_origin/" \
  > "$temporary_directory/headers.txt" || {
  failures+=("the public root headers could not be retrieved")
}

required_headers=(
  'x-content-type-options: nosniff'
  'x-frame-options: DENY'
  'referrer-policy: same-origin'
  'permissions-policy: camera=\(\), microphone=\(\), geolocation=\(\)'
)
for header in "${required_headers[@]}"; do
  header_name="${header%%:*}"
  header_value="${header#*: }"
  if ! grep -Eiq "^${header_name}:[[:space:]]*${header_value}[[:space:]]*$" "$temporary_directory/headers.txt"; then
    failures+=("required security header missing or incorrect: $header_name")
    echo "FAIL security header: $header_name"
  fi
done

csp="$(sed -n 's/^content-security-policy:[[:space:]]*//Ip' "$temporary_directory/headers.txt" | tr -d '\r')"
csp="$(sed -E 's/[[:space:]]*;[[:space:]]*/;/g; s/^[[:space:]]+//; s/[[:space:]]+$//' <<<"$csp")"
required_csp_directives=(
  "default-src 'self'"
  "script-src 'self' 'unsafe-inline'"
  "style-src 'self' 'unsafe-inline'"
  "img-src 'self' data: blob:"
  "font-src 'self' data:"
  "connect-src 'self' wss:"
  "frame-src 'self' blob:"
  "worker-src 'self' blob:"
  "media-src 'self' blob:"
  "manifest-src 'self'"
  "form-action 'self'"
  "frame-ancestors 'none'"
  "base-uri 'self'"
  "object-src 'none'"
  "upgrade-insecure-requests"
)
if [[ -z "$csp" ]]; then
  failures+=("required security header missing or incorrect: content-security-policy")
  echo "FAIL security header: content-security-policy"
else
  for directive in "${required_csp_directives[@]}"; do
    if [[ ";$csp;" != *";$directive;"* ]]; then
      failures+=("content-security-policy is missing directive: $directive")
      echo "FAIL CSP directive: $directive"
    fi
  done
fi

if [[ "$require_cloudflare" == true ]]; then
  if ! grep -Eiq '^server:[[:space:]]*cloudflare[[:space:]]*$' "$temporary_directory/headers.txt"; then
    failures+=("public response is not being served through Cloudflare")
    echo 'FAIL Cloudflare server header'
  fi
  if ! grep -Eiq '^cf-ray:[[:space:]]*[^[:space:]]+' "$temporary_directory/headers.txt"; then
    failures+=("Cloudflare request ID header is missing")
    echo 'FAIL Cloudflare request ID header'
  fi
fi

if ((${#failures[@]} > 0)); then
  printf '\nPublic health check failed:\n' >&2
  printf ' - %s\n' "${failures[@]}" >&2
  exit 1
fi

echo 'BTSP public health, readiness, Cloudflare routing, and security-header checks passed.'
