# BTSP Disaster Recovery Governance

## Purpose

Define recovery ownership, priorities, evidence, and coordinated procedures for database, configuration, workflows, notifications, application artifacts, and infrastructure.

## Recovery Governance

The Platform and Business Owners define recovery-time objective (RTO), recovery-point objective (RPO), data-retention obligations, and acceptable workflow interruption. Operations owns tested procedures. Security approves recovery access. Values must be recorded per deployment before go-live; unassigned RTO/RPO blocks production approval.

## Recovery Priorities

1. Personnel safety, incident containment, and evidence preservation
2. PostgreSQL integrity and authoritative data
3. Identity, roles, permissions, configuration, and workflow registry compatibility
4. Workflow instances and immutable snapshots
5. Application, Redis, Nginx, and frontend/backend availability
6. Notification queues/history and external delivery reconciliation
7. Business reconciliation and controlled reopening

## Database Recovery

PostgreSQL is the system of record. Follow `docs/runbooks/database-backup-restore.md`.

- Select a backup within the approved RPO.
- Verify checksum, encryption/access, source release, and Alembic revision.
- Restore into an isolated target first when time permits.
- Match the application artifact to the restored schema before running migrations.
- Validate core table counts, constraints, workflow versions, snapshots, and notification history.
- Record the precise data-loss interval.

## Configuration Recovery

- Configuration entries are included in PostgreSQL backups.
- Restore database state before applying code-owned defaults.
- Compare restored values to configuration-change snapshots and approved change records.
- Use idempotent seeds only to restore missing known defaults, not overwrite approved production customization without review.
- Confirm scoped-key uniqueness and active status.

## Workflow Recovery

- Restore registry-compatible application code and all referenced workflow definition versions.
- Verify every active instance references an existing definition code/version.
- Reconcile current state/status with latest workflow snapshots.
- Do not manually jump states to repair recovery discrepancies; use approved corrective actions or new audit events.
- Retired/deprecated definitions remain readable.

## Notification Recovery

- Restore templates and notification events from PostgreSQL.
- Identify queued, sent, skipped, and failed events at the recovery boundary.
- Do not blindly replay queued notifications; assess duplicate-delivery and business impact.
- Reconcile provider delivery records before marking sent or retrying.
- Keep webhook disabled until destination credentials and replay scope are verified.

## Application Recovery

- Deploy the last approved immutable Git tag/image digest.
- Restore production environment values from the approved secret/configuration store.
- Use `docker-compose.production.yml`; development mounts/reload are prohibited.
- Apply only migrations approved for the selected database/artifact combination.
- Validate health, readiness, login, registry, workflow reads, snapshots, and notifications.

## Infrastructure Recovery

- Rebuild the Docker host from approved operating-system and Docker prerequisites.
- Recreate protected networks, persistent volumes, DNS, TLS, firewall, logging, monitoring, and backup access.
- Confirm PostgreSQL and Redis are not exposed beyond approved boundaries.
- Restore Nginx routing and external ingress.
- Validate storage capacity and time synchronization.

## Disaster Declaration and Command

1. Incident Commander declares disaster and records start time/scope.
2. Security contains threats and preserves evidence.
3. Recovery Owner selects recovery point and artifact.
4. Business Owner approves RPO impact and workflow freeze.
5. Operators execute documented recovery with dual review for destructive steps.
6. Validation Owner runs technical and business checks.
7. Authorized owner approves reopening.

## Recovery Validation

- Database/Alembic revision matches application release.
- Health and readiness pass.
- Admin login and required permissions work.
- Workflow registry and definitions reconcile.
- Active instances and terminal history reconcile with snapshots.
- Configuration values match approved records.
- Notification history is readable and replay decision recorded.
- Frontend and Nginx routes work.
- Logs/metrics/backups resume.
- Business owner approves representative workflow reads/actions.

## Disaster Recovery Exercise

At least annually, and after material architecture/recovery changes:

- Restore a recent backup to isolated infrastructure.
- Deploy the matching immutable artifact.
- Measure actual RPO and RTO.
- Validate all recovery domains above.
- Exercise notification replay decision and credential recovery.
- Record participants, evidence, failures, corrective actions, owners, and deadlines.
- Update runbooks and governance documents.

Use the detailed checklist in `operational-checklists.md`.

## Communications and Records

Maintain incident timeline, decisions, approvals, backup identifiers, checksums, artifacts, commands, logs, validation evidence, data-loss interval, user communications, and corrective actions. Protect records from unauthorized access and secret exposure.
