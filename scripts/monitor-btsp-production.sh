#!/usr/bin/env bash
set -uo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

runtime_directory="${BTSP_MONITOR_DIRECTORY:-.runtime/monitoring}"
config_file="${BTSP_MONITOR_CONFIG_FILE:-$runtime_directory/monitor.env}"
mkdir -p "$runtime_directory"
chmod 700 "$runtime_directory" 2>/dev/null || true

if [[ -f "$config_file" ]]; then
  set -a
  # This protected file is maintained by the deployment owner.
  # shellcheck disable=SC1090
  source "$config_file"
  set +a
fi

event_log="$runtime_directory/events.jsonl"
state_file="$runtime_directory/last-state"
check_output="$runtime_directory/last-check.log"
max_log_bytes="${BTSP_MONITOR_LOG_MAX_BYTES:-10485760}"
max_log_archives="${BTSP_MONITOR_LOG_ARCHIVES:-7}"
disk_warning_percent="${BTSP_MONITOR_DISK_WARNING_PERCENT:-85}"
backup_max_age_hours="${BTSP_MONITOR_BACKUP_MAX_AGE_HOURS:-36}"
restart_warning_count="${BTSP_MONITOR_RESTART_WARNING_COUNT:-3}"
five_xx_warning_count="${BTSP_MONITOR_5XX_WARNING_COUNT:-5}"
lookback="${BTSP_MONITOR_LOG_LOOKBACK:-6m}"
alert_webhook_url="${BTSP_ALERT_WEBHOOK_URL:-}"

for numeric_value in \
  "$max_log_bytes" \
  "$max_log_archives" \
  "$disk_warning_percent" \
  "$backup_max_age_hours" \
  "$restart_warning_count" \
  "$five_xx_warning_count"
do
  if [[ ! "$numeric_value" =~ ^[0-9]+$ ]] || (( numeric_value < 1 )); then
    echo "BTSP monitor numeric settings must contain only positive integers." >&2
    exit 2
  fi
done
if (( disk_warning_percent > 100 )); then
  echo "BTSP_MONITOR_DISK_WARNING_PERCENT cannot exceed 100." >&2
  exit 2
fi

rotate_event_log() {
  local current_size=0
  if [[ -f "$event_log" ]]; then
    current_size="$(stat -c '%s' "$event_log" 2>/dev/null || echo 0)"
  fi
  if (( current_size < max_log_bytes )); then
    return
  fi

  local archive
  for ((archive=max_log_archives; archive>=1; archive--)); do
    if (( archive == max_log_archives )); then
      rm -f "$event_log.$archive"
    elif [[ -f "$event_log.$archive" ]]; then
      mv "$event_log.$archive" "$event_log.$((archive + 1))"
    fi
  done
  mv "$event_log" "$event_log.1"
}

append_event() {
  local status="$1"
  local summary="$2"
  local details="$3"
  STATUS="$status" SUMMARY="$summary" DETAILS="$details" python3 - "$event_log" <<'PY'
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import sys

record = {
    "timestamp": datetime.now(UTC).isoformat(),
    "event": "production_watchdog",
    "status": os.environ["STATUS"],
    "summary": os.environ["SUMMARY"],
    "details": [line for line in os.environ["DETAILS"].splitlines() if line],
}
with Path(sys.argv[1]).open("a", encoding="utf-8") as output:
    output.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
PY
}

send_webhook() {
  local status="$1"
  local summary="$2"
  local details="$3"
  if [[ -z "$alert_webhook_url" ]]; then
    return
  fi

  local payload
  payload="$(STATUS="$status" SUMMARY="$summary" DETAILS="$details" python3 - <<'PY'
import json
import os

print(json.dumps({
    "source": "BTSP production watchdog",
    "status": os.environ["STATUS"],
    "summary": os.environ["SUMMARY"],
    "details": [line for line in os.environ["DETAILS"].splitlines() if line],
}))
PY
)"
  curl --fail --silent --show-error --max-time 15 \
    --header 'Content-Type: application/json' \
    --data "$payload" \
    "$alert_webhook_url" >/dev/null
}

failures=()
check_lines=()

public_check_output="$("$repository_root/scripts/check-btsp-public-health.sh" 2>&1)"
public_check_status=$?
printf '%s\n' "$public_check_output" > "$check_output"
if (( public_check_status != 0 )); then
  failures+=("Public health or security-header validation failed")
else
  check_lines+=("Public health, readiness, and security headers passed")
fi

expected_containers=(postgres redis backend frontend nginx cloudflared)
for service in "${expected_containers[@]}"; do
  container_name="btsp-intranet-$service-1"
  container_state="$(docker inspect --format '{{.State.Status}}' "$container_name" 2>/dev/null || true)"
  if [[ "$container_state" != running ]]; then
    failures+=("$container_name is ${container_state:-missing}")
    continue
  fi

  container_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_name" 2>/dev/null || true)"
  if [[ "$container_health" != none && "$container_health" != healthy ]]; then
    failures+=("$container_name health is $container_health")
  fi

  restart_count="$(docker inspect --format '{{.RestartCount}}' "$container_name" 2>/dev/null || echo 0)"
  if [[ "$restart_count" =~ ^[0-9]+$ ]] && (( restart_count >= restart_warning_count )); then
    failures+=("$container_name has restarted $restart_count times")
  fi
done

disk_used_percent="$(df -P "$repository_root" | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')"
if [[ "$disk_used_percent" =~ ^[0-9]+$ ]] && (( disk_used_percent >= disk_warning_percent )); then
  failures+=("Host filesystem usage is ${disk_used_percent}%")
else
  check_lines+=("Host filesystem usage is ${disk_used_percent:-unknown}%")
fi

latest_backup="$(find .runtime/backups -maxdepth 1 -type f -name 'btsp-production-*.tar.gz.gpg' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 || true)"
if [[ -z "$latest_backup" ]]; then
  failures+=("No encrypted production backup was found")
else
  latest_backup_epoch="${latest_backup%% *}"
  latest_backup_epoch="${latest_backup_epoch%.*}"
  backup_age_hours=$(( ($(date +%s) - latest_backup_epoch) / 3600 ))
  if (( backup_age_hours > backup_max_age_hours )); then
    failures+=("Latest encrypted production backup is ${backup_age_hours} hours old")
  else
    check_lines+=("Latest encrypted production backup is ${backup_age_hours} hours old")
  fi
fi

recent_five_xx="$(
  docker logs btsp-intranet-nginx-1 --since "$lookback" 2>&1 |
    awk 'match($0, /"status":5[0-9][0-9]/) {count++} END {print count + 0}'
)"
if (( recent_five_xx >= five_xx_warning_count )); then
  failures+=("Nginx recorded $recent_five_xx server errors during the last $lookback")
else
  check_lines+=("Nginx recorded $recent_five_xx server errors during the last $lookback")
fi

if ((${#failures[@]} > 0)); then
  status="alert"
  summary="BTSP production monitoring detected ${#failures[@]} issue(s)"
  details="$(printf '%s\n' "${failures[@]}")"
else
  status="healthy"
  summary="BTSP production monitoring checks passed"
  details="$(printf '%s\n' "${check_lines[@]}")"
fi

fingerprint="$(printf '%s\n%s\n' "$status" "$details" | sha256sum | cut -d ' ' -f 1)"
previous_fingerprint="$(sed -n '2p' "$state_file" 2>/dev/null || true)"
previous_status="$(sed -n '1p' "$state_file" 2>/dev/null || true)"

rotate_event_log
append_event "$status" "$summary" "$details"
chmod 600 "$event_log" "$state_file" "$check_output" 2>/dev/null || true

notification_delivered=true
if [[ "$fingerprint" != "$previous_fingerprint" || "$status" != "$previous_status" ]]; then
  if ! send_webhook "$status" "$summary" "$details"; then
    echo "The monitoring webhook could not be delivered." >&2
    notification_delivered=false
  fi
fi
if [[ "$notification_delivered" == true ]]; then
  printf '%s\n%s\n' "$status" "$fingerprint" > "$state_file"
  chmod 600 "$state_file" 2>/dev/null || true
fi

echo "$summary"
if [[ "$status" == alert ]]; then
  printf ' - %s\n' "${failures[@]}"
  exit 1
fi
printf ' - %s\n' "${check_lines[@]}"
if [[ "$notification_delivered" != true ]]; then
  exit 1
fi
