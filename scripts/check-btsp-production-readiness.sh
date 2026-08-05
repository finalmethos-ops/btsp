#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

compose=(
  docker compose
  --env-file .env.intranet
  -p btsp-intranet
  -f docker-compose.yml
  -f docker-compose.production.yml
  -f docker-compose.intranet.yml
  -f docker-compose.tunnel.yml
)

echo "Checking public health and security headers..."
"$repository_root/scripts/check-btsp-public-health.sh"

echo "Checking production secret controls without displaying secret values..."
python3 "$repository_root/scripts/audit-btsp-production-secrets.py"

echo "Checking immutable deployment image integrity..."
python3 "$repository_root/scripts/audit-btsp-deployment-integrity.py"

expected_containers=(
  btsp-intranet-postgres-1
  btsp-intranet-redis-1
  btsp-intranet-backend-1
  btsp-intranet-frontend-1
  btsp-intranet-nginx-1
  btsp-intranet-cloudflared-1
)
for container_name in "${expected_containers[@]}"; do
  status="$(docker inspect --format '{{.State.Status}}' "$container_name" 2>/dev/null || true)"
  if [[ "$status" != running ]]; then
    echo "FAIL $container_name is $status" >&2
    exit 1
  fi
  case "$container_name" in
    *postgres-1|*redis-1|*backend-1|*frontend-1)
      health="$(docker inspect --format '{{.State.Health.Status}}' "$container_name")"
      if [[ "$health" != healthy ]]; then
        echo "FAIL $container_name health is $health" >&2
        exit 1
      fi
      ;;
  esac
  echo "PASS $container_name"
done

cloudflared_count="$(docker ps --format '{{.Names}}' --filter 'name=btsp-intranet-cloudflared' | wc -l | tr -d ' ')"
if [[ "$cloudflared_count" != 1 ]]; then
  echo "FAIL expected exactly one managed Cloudflare connector; found $cloudflared_count" >&2
  exit 1
fi

metrics="$(docker run --rm --network btsp-intranet_default alpine:3.20 sh -c 'wget -qO- http://cloudflared:20241/metrics')"
total_requests="$(
  awk '$1 == "cloudflared_tunnel_total_requests" {value=$2} END {print value}' <<<"$metrics"
)"
request_errors="$(
  awk '$1 == "cloudflared_tunnel_request_errors" {value=$2} END {print value}' <<<"$metrics"
)"
if [[ -z "$total_requests" || "$total_requests" -lt 1 ]]; then
  echo "FAIL Cloudflare connector has not proxied a request" >&2
  exit 1
fi
if [[ -z "$request_errors" ]]; then
  echo "FAIL Cloudflare connector did not expose its origin error counter" >&2
  exit 1
fi
echo "PASS Cloudflare connector is currently reachable after $total_requests proxied request(s); cumulative origin errors: $request_errors"

if command -v powershell.exe >/dev/null 2>&1; then
  task_result="$(powershell.exe -NoProfile -Command '(Get-ScheduledTaskInfo -TaskName "BTSP Production Backup").LastTaskResult' | tr -d '\r')"
  if [[ "$task_result" != 0 ]]; then
    echo "FAIL scheduled backup task result is $task_result" >&2
    exit 1
  fi
  echo "PASS scheduled backup task result is 0"
fi

echo "BTSP production readiness checks passed."
