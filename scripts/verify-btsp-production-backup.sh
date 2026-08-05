#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <btsp-production-backup.tar.gz.gpg>" >&2
  exit 2
fi

backup_file="$1"
checksum_file="$backup_file.sha256"
passphrase_file="${BTSP_BACKUP_PASSPHRASE_FILE:-.runtime/backup-secrets/archive-passphrase}"
postgres_image="$(
  docker inspect btsp-intranet-postgres-1 \
    --format '{{.Config.Image}}' 2>/dev/null ||
    printf '%s' 'postgres:16-alpine'
)"

for required_file in "$backup_file" "$checksum_file" "$passphrase_file"; do
  if [[ ! -f "$required_file" || ! -s "$required_file" ]]; then
    echo "Required backup verification file is missing or empty: $required_file" >&2
    exit 3
  fi
done

sha256sum --check "$checksum_file"

gpg \
  --batch \
  --quiet \
  --pinentry-mode loopback \
  --passphrase-file "$passphrase_file" \
  --decrypt "$backup_file" |
docker run --rm --interactive \
  --tmpfs /restore:rw,nosuid,size=2g \
  "$postgres_image" \
  sh -ceu '
    mkdir -p /restore/archive /restore/postgres /restore/socket
    tar -xzf - -C /restore/archive
    for required_path in \
      database.dump \
      database-contents.txt \
      manifest.env \
      attachments \
      purchase-order-exports \
      analytics-reports \
      invoice-intake \
      .env.intranet \
      tls/authority/btsp-intranet-ca.key \
      tls/server/server.key \
      cloudflare/tunnel-token
    do
      test -e "/restore/archive/$required_path"
    done
    pg_restore --list /restore/archive/database.dump >/dev/null
    chown -R postgres:postgres /restore/postgres /restore/socket
    gosu postgres initdb \
      --pgdata /restore/postgres \
      --username postgres \
      --auth trust \
      --no-locale >/dev/null
    gosu postgres pg_ctl \
      --pgdata /restore/postgres \
      --options "-k /restore/socket -p 55432" \
      --wait \
      start >/dev/null
    stop_postgres() {
      gosu postgres pg_ctl \
        --pgdata /restore/postgres \
        --mode fast \
        --wait \
        stop >/dev/null 2>&1 || true
    }
    trap stop_postgres EXIT INT TERM
    gosu postgres createdb \
      --host /restore/socket \
      --port 55432 \
      --username postgres \
      btsp_restore
    gosu postgres pg_restore \
      --host /restore/socket \
      --port 55432 \
      --username postgres \
      --dbname btsp_restore \
      --no-owner \
      --no-acl \
      /restore/archive/database.dump
    restored_revision="$(
      gosu postgres psql \
        --host /restore/socket \
        --port 55432 \
        --username postgres \
        --dbname btsp_restore \
        --tuples-only \
        --no-align \
        --command "SELECT version_num FROM alembic_version;"
    )"
    restored_tables="$(
      gosu postgres psql \
        --host /restore/socket \
        --port 55432 \
        --username postgres \
        --dbname btsp_restore \
        --tuples-only \
        --no-align \
        --command "SELECT count(*) FROM pg_tables WHERE schemaname = '"'"'public'"'"';"
    )"
    expected_revision="$(
      sed -n "s/^alembic_revision=//p" /restore/archive/manifest.env
    )"
    expected_tables="$(
      sed -n "s/^public_table_count=//p" /restore/archive/manifest.env
    )"
    test "$restored_revision" = "$expected_revision"
    test "$restored_tables" = "$expected_tables"
    printf "Disposable restore: passed\n"
    printf "Alembic revision: %s\n" "$restored_revision"
    printf "Public tables: %s\n" "$restored_tables"
    stop_postgres
    trap - EXIT INT TERM
  '

echo "Backup checksum, encryption, protected files, and disposable database restore passed."
