#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

r2_environment_file="${BTSP_R2_ENV_FILE:-.runtime/backup-secrets/r2.env}"
rclone_image="${BTSP_RCLONE_IMAGE:-rclone/rclone:1.74.4@sha256:c61954aaa32328a5486715dd063a81c7879f5195ad3505cd362deddd509dc4a1}"

if [[ ! -s "$r2_environment_file" ]]; then
  echo "R2 backup credentials are not configured: $r2_environment_file" >&2
  exit 3
fi

required_r2_variables=(
  BTSP_R2_BUCKET
  RCLONE_CONFIG_R2_TYPE
  RCLONE_CONFIG_R2_PROVIDER
  RCLONE_CONFIG_R2_ACCESS_KEY_ID
  RCLONE_CONFIG_R2_SECRET_ACCESS_KEY
  RCLONE_CONFIG_R2_ENDPOINT
  RCLONE_CONFIG_R2_ACL
  RCLONE_CONFIG_R2_NO_CHECK_BUCKET
)
for variable_name in "${required_r2_variables[@]}"; do
  if ! grep -Eq "^${variable_name}=.+" "$r2_environment_file"; then
    echo "Required R2 setting is missing: $variable_name" >&2
    exit 4
  fi
done

r2_bucket="$(python3 - "$r2_environment_file" <<'PY'
from pathlib import Path
import sys

for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and key == "BTSP_R2_BUCKET":
        print(value.strip())
        break
PY
)"
if [[ ! "$r2_bucket" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]]; then
  echo "BTSP_R2_BUCKET is not a valid R2 bucket name." >&2
  exit 5
fi

temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/btsp-r2-restore.XXXXXX")"
cleanup() {
  local status=$?
  trap - EXIT
  rm -rf "$temporary_directory"
  exit "$status"
}
trap cleanup EXIT

rclone() {
  docker run --rm \
    --env-file "$r2_environment_file" \
    --volume "$temporary_directory:/data" \
    "$rclone_image" \
    "$@"
}

latest_object="$(
  rclone lsf \
    "r2:${r2_bucket}/production" \
    --recursive \
    --files-only \
    --include 'btsp-production-*.tar.gz.gpg' |
    sort |
    tail -n 1
)"
if [[ ! "$latest_object" =~ ^[0-9]{4}/[0-9]{2}/btsp-production-[0-9]{8}T[0-9]{6}Z\.tar\.gz\.gpg$ ]]; then
  echo "No valid encrypted production archive was found in private R2 storage." >&2
  exit 6
fi

archive_name="$(basename "$latest_object")"
checksum_name="$archive_name.sha256"
remote_directory="r2:${r2_bucket}/production/$(dirname "$latest_object")"
rclone copyto "$remote_directory/$archive_name" "/data/$archive_name"
rclone copyto "$remote_directory/$checksum_name" "/data/$checksum_name"

echo "Downloaded and verifying offsite archive: $latest_object"
BTSP_BACKUP_PASSPHRASE_FILE="${BTSP_BACKUP_PASSPHRASE_FILE:-.runtime/backup-secrets/archive-passphrase}" \
  "$repository_root/scripts/verify-btsp-production-backup.sh" "/$temporary_directory/$archive_name"
echo "Offsite R2 download, checksum, encryption, and disposable restore passed."
