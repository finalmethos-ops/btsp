#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

environment_file="${BTSP_ENV_FILE:-.env.intranet}"
project_name="${BTSP_COMPOSE_PROJECT:-btsp-intranet}"
backup_directory="${BTSP_BACKUP_DIRECTORY:-.runtime/backups}"
secret_directory="${BTSP_BACKUP_SECRET_DIRECTORY:-.runtime/backup-secrets}"
passphrase_file="$secret_directory/archive-passphrase"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_directory/btsp-production-$timestamp.tar.gz.gpg"
partial_backup_file="$backup_file.partial"
checksum_file="$backup_file.sha256"

compose=(
  docker compose
  --env-file "$environment_file"
  -p "$project_name"
  -f docker-compose.yml
  -f docker-compose.production.yml
  -f docker-compose.intranet.yml
  -f docker-compose.tunnel.yml
)

required_files=(
  "$environment_file"
  .runtime/tls/authority/btsp-intranet-ca.crt
  .runtime/tls/authority/btsp-intranet-ca.key
  .runtime/tls/server/server.crt
  .runtime/tls/server/server.key
  .runtime/cloudflare/tunnel-token
)

for required_file in "${required_files[@]}"; do
  if [[ ! -f "$required_file" || ! -s "$required_file" ]]; then
    echo "Required protected file is missing or empty: $required_file" >&2
    exit 2
  fi
done

mkdir -p "$backup_directory" "$secret_directory"
chmod 700 "$backup_directory" "$secret_directory" 2>/dev/null || true

if [[ ! -s "$passphrase_file" ]]; then
  openssl rand -base64 -out "$passphrase_file" 48
  chmod 600 "$passphrase_file" 2>/dev/null || true
  echo "Generated the backup recovery passphrase at $passphrase_file." >&2
  echo "Copy that file to a separate protected offline location." >&2
fi

exec 9>"$backup_directory/.backup.lock"
if ! flock -n 9; then
  echo "Another BTSP backup is already running." >&2
  exit 3
fi

git_revision="$(git rev-parse HEAD)"
app_version="$(
  python3 - "$environment_file" <<'PY'
from pathlib import Path
import sys

for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("APP_VERSION="):
        print(line.split("=", 1)[1])
        break
else:
    print("unknown")
PY
)"

cleanup() {
  local status=$?
  trap - EXIT

  if (( status != 0 )) && [[ -f "$partial_backup_file" ]]; then
    mv "$partial_backup_file" "$backup_file.failed"
    echo "Incomplete encrypted output retained for diagnosis: $backup_file.failed" >&2
  fi
  exit "$status"
}

trap cleanup EXIT

for service in postgres redis backend frontend nginx cloudflared; do
  container_id="$("${compose[@]}" ps -q "$service")"
  if [[ -z "$container_id" ]] ||
    [[ "$(docker inspect --format '{{.State.Status}}' "$container_id")" != "running" ]]; then
    echo "Required production service is not running: $service" >&2
    exit 4
  fi
done
postgres_container_id="$("${compose[@]}" ps -q postgres)"
postgres_image="$(
  docker inspect "$postgres_container_id" --format '{{.Config.Image}}'
)"

echo "Capturing a live two-pass durable-file snapshot and PostgreSQL dump into $backup_file."
docker run --rm \
  --network "${project_name}_default" \
  --env-file "$environment_file" \
  --env "BACKUP_TIMESTAMP=$timestamp" \
  --env "BACKUP_GIT_REVISION=$git_revision" \
  --env "BACKUP_APP_VERSION=$app_version" \
  --volume "${project_name}_attachment_data:/source/attachments:ro" \
  --volume "${project_name}_purchase_order_export_data:/source/purchase-order-exports:ro" \
  --volume "${project_name}_analytics_report_data:/source/analytics-reports:ro" \
  --volume "${project_name}_invoice_intake_data:/source/invoice-intake:ro" \
  --volume "$repository_root/$environment_file:/protected/.env.intranet:ro" \
  --volume "$repository_root/.runtime/tls:/protected/tls:ro" \
  --volume "$repository_root/.runtime/cloudflare/tunnel-token:/protected/cloudflare/tunnel-token:ro" \
  --tmpfs /staging:rw,noexec,nosuid,size=1g \
  "$postgres_image" \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    # Application files are immutable after creation in normal workflows. A
    # pass on either side of pg_dump ensures every file referenced by the
    # database snapshot is retained without stopping public traffic. Files
    # removed concurrently may remain as harmless unreferenced recovery data.
    for directory in \
      attachments \
      purchase-order-exports \
      analytics-reports \
      invoice-intake
    do
      mkdir -p "/staging/$directory"
      cp -a "/source/$directory/." "/staging/$directory/"
    done
    pg_dump \
      --host postgres \
      --username "$POSTGRES_USER" \
      --dbname "$POSTGRES_DB" \
      --format custom \
      --no-owner \
      --no-acl \
      --file /staging/database.dump
    pg_restore --list /staging/database.dump > /staging/database-contents.txt
    for directory in \
      attachments \
      purchase-order-exports \
      analytics-reports \
      invoice-intake
    do
      cp -a "/source/$directory/." "/staging/$directory/"
    done
    alembic_revision="$(
      psql \
        --host postgres \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --tuples-only \
        --no-align \
        --command "SELECT version_num FROM alembic_version;"
    )"
    public_table_count="$(
      psql \
        --host postgres \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --tuples-only \
        --no-align \
        --command "SELECT count(*) FROM pg_tables WHERE schemaname = '"'"'public'"'"';"
    )"
    {
      printf "format=btsp-production-backup-v1\n"
      printf "created_at=%s\n" "$BACKUP_TIMESTAMP"
      printf "app_version=%s\n" "$BACKUP_APP_VERSION"
      printf "git_revision=%s\n" "$BACKUP_GIT_REVISION"
      printf "alembic_revision=%s\n" "$alembic_revision"
      printf "public_table_count=%s\n" "$public_table_count"
      for directory in \
        attachments \
        purchase-order-exports \
        analytics-reports \
        invoice-intake
      do
        file_count="$(find "/staging/$directory" -type f | wc -l)"
        kibibytes="$(du -sk "/staging/$directory" | cut -f1)"
        printf "%s_files=%s\n" "$directory" "$file_count"
        printf "%s_kibibytes=%s\n" "$directory" "$kibibytes"
      done
    } > /staging/manifest.env
    cp -a /protected/.env.intranet /staging/
    cp -a /protected/tls /staging/
    cp -a /protected/cloudflare /staging/
    tar -C /staging -czf - .
  ' |
  gpg \
    --batch \
    --yes \
    --pinentry-mode loopback \
    --passphrase-file "$passphrase_file" \
    --symmetric \
    --cipher-algo AES256 \
    --compress-algo none \
    --output "$partial_backup_file"

mv "$partial_backup_file" "$backup_file"
chmod 600 "$backup_file" 2>/dev/null || true
sha256sum "$backup_file" > "$checksum_file"
chmod 600 "$checksum_file" 2>/dev/null || true

"$repository_root/scripts/verify-btsp-production-backup.sh" "$backup_file"

echo "Encrypted BTSP backup completed and verified:"
echo "$backup_file"
echo "$checksum_file"
