# BTSP 001P Rollback Plan

## Objective

Restore the last verified application and database state when an 001P deployment cannot be safely corrected in place.

## Preconditions

- A verified pre-deployment PostgreSQL backup exists off the application volume.
- The previously deployed image tags or source revision are available.
- The maintenance owner has database, Docker host, and administrator credentials.
- The rollback window and expected data loss boundary are approved.

## Rollback Procedure

1. Stop user traffic and record the incident timestamp.
2. Capture current container logs and, when safe, a final failed-state database backup.
3. Stop application-facing services:

   ```bash
   docker compose stop nginx frontend backend
   ```

4. Keep PostgreSQL stopped while restoring:

   ```bash
   docker compose stop postgres
   ```

5. Restore the verified pre-deployment database using `docs/runbooks/database-backup-restore.md`.
6. Revert the repository checkout or deployment manifest to the previous immutable release tag.
7. Rebuild or pull the previous application images.
8. Start PostgreSQL and Redis, then backend, frontend, and Nginx:

   ```bash
   docker compose up -d postgres redis
   docker compose up -d backend frontend nginx
   ```

9. Run health and readiness checks.
10. Verify administrator login.
11. Verify the workflow registry and `BPP_PURCHASING` definition match the restored release.
12. Verify configuration, snapshots, and notification history are readable.
13. Confirm seed tables contain no partial duplicates before rerunning any seed.
14. Reopen traffic only after technical and business owners approve.

## Database Strategy

Restoring the pre-deployment backup is preferred over Alembic downgrade. Downgrading from `0008` drops notification tables; downgrading from `0007` removes workflow metadata and explicit states. Both operations can destroy release data.

If a schema-only downgrade is explicitly approved, test it against a disposable restored copy first and preserve a fresh backup of the failed environment.

## Post-Rollback Verification

- `GET /api/v1/health` returns `{"status":"ok"}`.
- `GET /api/v1/ready` returns `{"status":"ready"}`.
- Administrator login and `/auth/me` succeed.
- Workflow registry list/detail succeed.
- No workflow instance references a definition version absent from the restored database.
- Configuration uniqueness checks show no duplicate scoped keys.
- Permission and role assignments match the previous release.
- Snapshot and notification counts align with the approved recovery point.
- All containers remain stable and logs contain no repeated tracebacks.

## Rollback Record

Record the restored backup identifier, previous and failed release revisions, operator, start/end timestamps, validation evidence, data-loss interval, and authorization to reopen traffic.
