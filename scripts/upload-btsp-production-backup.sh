#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

backup_directory="${BTSP_BACKUP_DIRECTORY:-.runtime/backups}"
r2_environment_file="${BTSP_R2_ENV_FILE:-.runtime/backup-secrets/r2.env}"
rclone_image="${BTSP_RCLONE_IMAGE:-rclone/rclone:1.74.4@sha256:c61954aaa32328a5486715dd063a81c7879f5195ad3505cd362deddd509dc4a1}"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [btsp-production-backup.tar.gz.gpg]" >&2
  exit 2
fi

if [[ ! -f "$r2_environment_file" || ! -s "$r2_environment_file" ]]; then
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

r2_bucket="$(
  python3 - "$r2_environment_file" <<'PY'
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

if [[ $# -eq 1 ]]; then
  backup_file="$1"
else
  backup_file="$(
    find "$backup_directory" \
      -maxdepth 1 \
      -type f \
      -name 'btsp-production-*.tar.gz.gpg' \
      -printf '%p\n' |
      sort |
      tail -n 1
  )"
fi
if [[ -z "${backup_file:-}" || ! -f "$backup_file" ]]; then
  echo "No completed encrypted BTSP production backup was found." >&2
  exit 6
fi

checksum_file="$backup_file.sha256"
"$repository_root/scripts/verify-btsp-production-backup.sh" "$backup_file"

backup_basename="$(basename "$backup_file")"
checksum_basename="$(basename "$checksum_file")"
if [[ ! "$backup_basename" =~ ^btsp-production-([0-9]{4})([0-9]{2})[0-9]{2}T[0-9]{6}Z\.tar\.gz\.gpg$ ]]; then
  echo "The backup filename does not contain a valid UTC production timestamp." >&2
  exit 7
fi
remote_prefix="production/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
remote_directory="r2:${r2_bucket}/${remote_prefix}"
absolute_backup_directory="$(cd "$(dirname "$backup_file")" && pwd)"

rclone() {
  docker run --rm \
    --env-file "$r2_environment_file" \
    --volume "$absolute_backup_directory:/data:ro" \
    "$rclone_image" \
    "$@"
}

echo "Uploading verified encrypted backup to private R2 storage."
rclone copyto \
  "/data/$backup_basename" \
  "$remote_directory/$backup_basename" \
  --s3-upload-cutoff 100M \
  --s3-chunk-size 100M
rclone copyto \
  "/data/$checksum_basename" \
  "$remote_directory/$checksum_basename" \
  --s3-upload-cutoff 100M \
  --s3-chunk-size 100M

rclone check \
  /data \
  "$remote_directory" \
  --include "/$backup_basename" \
  --include "/$checksum_basename" \
  --one-way \
  --download

echo "Encrypted offsite backup upload and content verification passed:"
echo "$remote_directory/$backup_basename"
echo "$remote_directory/$checksum_basename"
