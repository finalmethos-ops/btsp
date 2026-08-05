#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded concurrency test for the live-presentation ordering endpoint.
# It is intentionally dry-run by default. Run this against an isolated test
# event; repeated PUTs update the same entity/slide order and are not a way to
# generate production business volume.

BASE_URL="${BASE_URL:-http://localhost:18080/api/v1}"
SUB_EVENT_ID="${SUB_EVENT_ID:-}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
PAYLOAD="${PAYLOAD:-{\"quantity\":1}}"
REQUESTS="${REQUESTS:-100}"
CONCURRENCY="${CONCURRENCY:-16}"
DRY_RUN="${DRY_RUN:-1}"

if [[ -z "$SUB_EVENT_ID" ]]; then
  echo "SUB_EVENT_ID is required." >&2
  exit 2
fi
if [[ -z "$AUTH_TOKEN" ]]; then
  echo "AUTH_TOKEN is required." >&2
  exit 2
fi
if ! [[ "$REQUESTS" =~ ^[1-9][0-9]*$ && "$CONCURRENCY" =~ ^[1-9][0-9]*$ ]]; then
  echo "REQUESTS and CONCURRENCY must be positive integers." >&2
  exit 2
fi

if [[ "$BASE_URL" == *"purchasing-events.us"* ]]; then
  if [[ "${ALLOW_PRODUCTION_ORDER_LOAD:-}" != "YES" || \
    "${PRODUCTION_ORDER_LOAD_CONFIRM:-}" != "I_UNDERSTAND_THIS_WRITES_TEST_ORDERS" ]]; then
    echo "Refusing to send order writes to the production hostname." >&2
    echo "Use an isolated target, or provide both explicit production safeguards." >&2
    exit 3
  fi
fi

ENDPOINT="${BASE_URL%/}/event-ordering/${SUB_EVENT_ID}/order"
echo "Endpoint: $ENDPOINT"
echo "Requests: $REQUESTS; concurrency: $CONCURRENCY; dry-run: $DRY_RUN"
echo "Payload: $PAYLOAD"

if [[ "$DRY_RUN" != "0" ]]; then
  echo "Dry run only; no requests were sent. Set DRY_RUN=0 for an isolated test event."
  exit 0
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v xargs >/dev/null 2>&1; then
  echo "curl and xargs are required." >&2
  exit 2
fi

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
export AUTH_TOKEN ENDPOINT PAYLOAD work_dir

started="$(date +%s)"
seq 1 "$REQUESTS" | xargs -P "$CONCURRENCY" -I{} sh -c '
  curl --silent --show-error --max-time 30 \
    -o "$work_dir/{}.body" \
    -w "%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    --data "$PAYLOAD" \
    "$ENDPOINT" >"$work_dir/{}.status" 2>"$work_dir/{}.error" || echo 000 >"$work_dir/{}.status"
'
finished="$(date +%s)"

echo "Completed in $((finished - started)) second(s)."
echo "HTTP status counts:"
for status in $(cat "$work_dir"/*.status | sort -u); do
  count="$(grep -hxc "$status" "$work_dir"/*.status | awk '{ total += $1 } END { print total + 0 }')"
  printf '  %s: %s\n' "$status" "$count"
done

failures="$(awk '$0 !~ /^2[0-9][0-9]$/' "$work_dir"/*.status | wc -l | tr -d ' ')"
if [[ "$failures" != "0" ]]; then
  echo "Non-2xx responses: $failures" >&2
  first_error="$(find "$work_dir" -name '*.error' -type f -size +0c -print -quit || true)"
  if [[ -n "$first_error" ]]; then
    echo "First curl error:" >&2
    sed -n '1,3p' "$first_error" >&2
  fi
  exit 1
fi

echo "All requests returned a 2xx status."
