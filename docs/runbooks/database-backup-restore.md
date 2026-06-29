# BTSP PostgreSQL Backup and Restore Runbook

## Purpose

Create, transfer, restore, and validate BTSP PostgreSQL backups before deployment, migration, or rollback.

Purchase-request file content resides in the `attachment_data` Docker volume. Back up that volume
at the same maintenance boundary as PostgreSQL so attachment metadata and content remain consistent.
Pause application writes while capturing both assets. After restore, download a representative
attachment and compare its SHA-256 value with `purchase_request_attachments.sha256`.

Purchase Order PDFs and structured exports reside in the `purchase_order_export_data` volume. Capture
it with the database and attachment volume, then verify a restored artifact against
`purchase_order_artifacts.sha256`.

## Backup Policy

- Take a verified backup immediately before every migration or deployment.
- Store backups off the PostgreSQL Docker volume.
- Encrypt backups and restrict access.
- Record database name, release revision, Alembic revision, timestamp, and operator.
- Test restores regularly in a disposable environment.

## Logical Backup with pg_dump

Custom format is recommended for selective and parallel restore:

```bash
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --format=custom \
  --no-owner \
  --file=/tmp/btsp-predeploy.dump

docker compose cp postgres:/tmp/btsp-predeploy.dump ./backups/btsp-predeploy.dump
```

Verify the archive before relying on it:

```bash
docker compose exec -T postgres pg_restore --list /tmp/btsp-predeploy.dump
```

For plain SQL:

```bash
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --no-owner > ./backups/btsp-predeploy.sql
```

## PostgreSQL Volume Backup

Stop application writes before a filesystem-level volume backup:

```bash
docker compose stop nginx frontend backend
docker compose stop postgres
docker run --rm \
  -v btsp_postgres_data:/volume:ro \
  -v "$(pwd)/backups:/backup" \
  alpine tar -czf /backup/btsp-postgres-volume.tgz -C /volume .
docker compose start postgres backend frontend nginx
```

The actual Compose volume name can differ by project name. Confirm it with `docker volume ls`. Logical `pg_dump` remains the portable primary backup.

## Restore a Custom-Format Backup

Use a maintenance window and prevent application writes:

```bash
docker compose stop nginx frontend backend
docker compose cp ./backups/btsp-predeploy.dump postgres:/tmp/btsp-restore.dump

docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" \
  -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();"

docker compose exec -T postgres dropdb \
  -U "$POSTGRES_USER" \
  --if-exists "$POSTGRES_DB"

docker compose exec -T postgres createdb \
  -U "$POSTGRES_USER" \
  "$POSTGRES_DB"

docker compose exec -T postgres pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  /tmp/btsp-restore.dump
```

Do not run Alembic automatically after rollback unless the restored application version expects a newer schema. First inspect `alembic_version` and match the application artifact to the restored database.

## Restore a Plain SQL Backup

After recreating the target database:

```bash
docker compose cp ./backups/btsp-predeploy.sql postgres:/tmp/btsp-restore.sql
docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f /tmp/btsp-restore.sql
```

## Post-Restore Validation

```bash
docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -c "SELECT version_num FROM alembic_version;"

docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM workflow_definitions; SELECT count(*) FROM workflow_instances; SELECT count(*) FROM event_snapshots; SELECT count(*) FROM notification_events;"
```

Then start services and verify:

- Health and readiness
- Administrator login
- Workflow registry and active BPP definition
- Configuration entries and unique scoped keys
- Snapshot readability and expected counts
- Notification template/event readability
- A read-only business verification approved by the workflow owner

## Restore Record

Record archive checksum, source environment, target environment, database/Alembic versions, operator, start/end timestamps, validation results, and authorization to resume writes.
