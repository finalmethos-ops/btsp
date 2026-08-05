# BTSP PostgreSQL Backup and Restore Runbook

## Purpose

Create, transfer, restore, and validate BTSP PostgreSQL backups before deployment, migration, or rollback.

Purchase-request file content resides in the `attachment_data` Docker volume. Back up that volume
with a two-pass durable-file snapshot around PostgreSQL's consistent `pg_dump`
snapshot. This keeps attachment metadata and content recoverable without
stopping the public application. Files removed during the backup may remain as
harmless unreferenced recovery data. After restore, download a representative
attachment and compare its SHA-256 value with `purchase_request_attachments.sha256`.

Purchase Order PDFs and structured exports reside in the `purchase_order_export_data` volume. Capture
it with the database and attachment volume, then verify a restored artifact against
`purchase_order_artifacts.sha256`.

## Backup Policy

- Take a verified backup immediately before every migration or deployment.
- Run the encrypted production backup daily.
- Store backups off the PostgreSQL Docker volume.
- Encrypt backups and restrict access.
- Record database name, release revision, Alembic revision, timestamp, and operator.
- Test restores regularly in a disposable environment.

## Encrypted Production Recovery Bundle

From the repository root:

```bash
./scripts/backup-btsp-production.sh
```

This command keeps Nginx and the backend online while it captures:

- a portable PostgreSQL custom-format dump;
- attachments, purchase-order exports, analytics reports, and invoice intake;
- the active intranet environment file;
- the private origin certificate authority and server certificate;
- the Cloudflare Tunnel token.

The stream is encrypted with AES-256 before it reaches disk. The command
validates the SHA-256 checksum, decrypts the archive inside a Docker `tmpfs`,
and performs a disposable PostgreSQL restore. A backup is successful only
after the Alembic revision and public-table count match.

The encryption passphrase is generated at:

```text
.runtime/backup-secrets/archive-passphrase
```

Copy that passphrase to an offline password vault or encrypted removable drive.
Do not upload it to the same R2 bucket as the archives. Losing the passphrase
makes every encrypted archive unrecoverable.

On Windows, restrict both backup-secret files to the current user,
Administrators, and SYSTEM:

```powershell
icacls .runtime\backup-secrets /inheritance:r
icacls .runtime\backup-secrets /grant:r `
  "$env:USERNAME:(OI)(CI)F" `
  "Administrators:(OI)(CI)F" `
  "SYSTEM:(OI)(CI)F"
```

## Private Cloudflare R2 Offsite Copy

Create a private R2 bucket named `btsp-production-backups` using the Standard
storage class. Create an R2 API token with Object Read & Write permission
limited to that bucket. Do not enable public access.

Save the following locally as `.runtime/backup-secrets/r2.env`; replace the
three placeholder values and do not paste the credentials into chat:

```dotenv
BTSP_R2_BUCKET=btsp-production-backups
RCLONE_CONFIG_R2_TYPE=s3
RCLONE_CONFIG_R2_PROVIDER=Cloudflare
RCLONE_CONFIG_R2_ACCESS_KEY_ID=REPLACE_WITH_ACCESS_KEY_ID
RCLONE_CONFIG_R2_SECRET_ACCESS_KEY=REPLACE_WITH_SECRET_ACCESS_KEY
RCLONE_CONFIG_R2_ENDPOINT=https://REPLACE_WITH_ACCOUNT_ID.r2.cloudflarestorage.com
RCLONE_CONFIG_R2_ACL=private
RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
```

Upload the latest completed archive only after its local disposable restore
passes:

```bash
./scripts/upload-btsp-production-backup.sh
```

Run backup, restore verification, upload, and remote content comparison as one
operation:

```bash
./scripts/backup-and-upload-btsp-production.sh
```

## Nightly Windows Schedule

Docker Desktop must be running and the Windows user must be signed in because
the scheduled task uses an interactive WSL session. The registration script
runs WSL through a hidden `wscript.exe` launcher under
`.runtime\task-launchers`, so the nightly job does not open a console window.
Register the task from a PowerShell window at the repository root:

```powershell
.\scripts\register-btsp-backup-task.ps1 -Distro Ubuntu -At 02:00
```

The task starts when the computer becomes available after a missed run, allows
up to two hours, and writes its output to:

```text
.runtime\backup-logs\nightly.log
```

Run this check after registration:

```powershell
Get-ScheduledTask -TaskName "BTSP Production Backup" |
  Get-ScheduledTaskInfo
```

To run it immediately for a smoke test:

```powershell
Start-ScheduledTask -TaskName "BTSP Production Backup"
Get-Content .runtime\backup-logs\nightly.log -Wait
```

The script is safe to run repeatedly; each run creates a timestamped archive
and uploads it beneath `production/YYYY/MM/`.

The uploader uses a digest-pinned rclone 1.74.4 container and stores objects
under `production/YYYY/MM/`. Configure an R2 lifecycle rule for that prefix
only after the organization chooses a documented retention period. A practical
starting policy is 90 daily backups plus 12 monthly recovery points.

After the first upload, download one encrypted archive and checksum into a
separate temporary directory and run:

```bash
./scripts/verify-btsp-r2-backup.sh
```

Perform that offsite-download recovery drill at least quarterly.

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
