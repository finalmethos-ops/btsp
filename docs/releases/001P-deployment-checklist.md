# BTSP 001P Deployment and Go-Live Checklist

## Release Artifact

- [ ] Deployment uses a reviewed, committed Git revision.
- [ ] Release revision and image tags are recorded.
- [ ] `docs/validation/001P-production-validation.md` is accepted.
- [ ] Open items in `001P-known-issues.md` are accepted by the owner.

## Host and Environment

- [ ] Docker Engine and Docker Compose are installed.
- [ ] Repository is cloned to the approved host path.
- [ ] `.env` is created from `.env.example` and is not committed.
- [ ] `ENVIRONMENT=production`.
- [ ] `SECRET_KEY` is unique and not the tracked default.
- [ ] `BOOTSTRAP_ADMIN_TOKEN` is unique and not the tracked default.
- [ ] PostgreSQL credentials are not local defaults.
- [ ] CORS origins list only approved HTTPS origins.
- [ ] Persistent PostgreSQL volume is configured and backed up.
- [ ] Redis is reachable from the backend network.
- [ ] Nginx ports, DNS, TLS, and routing are approved.

## Backup and Build

- [ ] Pre-deployment PostgreSQL backup is complete.
- [ ] Backup restore was validated in a non-production database.
- [ ] Production override is included in every Compose command.
- [ ] Production Compose `config` passes.
- [ ] Production Compose `build` passes cleanly.
- [ ] Production Compose `up -d` completes.
- [ ] `docker compose ps` shows expected services and healthy dependencies.

## Database and Application

- [ ] `docker compose exec backend alembic upgrade head` passes.
- [ ] Alembic current revision is `0008_notification_framework`.
- [ ] Backend tests and Ruff pass in the release containers.
- [ ] Frontend build and tests pass in the release container.
- [ ] Backend, frontend, PostgreSQL, Redis, and Nginx logs were reviewed.

## Bootstrap and Seeds

- [ ] Initial administrator is bootstrapped.
- [ ] Administrator password is changed from the initial value.
- [ ] Bootstrap token is rotated after provisioning.
- [ ] Platform configuration defaults are seeded.
- [ ] Workflow registry defaults are verified.
- [ ] BPP purchasing definition is seeded.
- [ ] BPP approval policies are seeded.
- [ ] BPP notification configuration and templates are seeded.
- [ ] Repeated seed verification shows no duplicate records.

## Operational Checks

- [ ] Health endpoint returns `ok`.
- [ ] Readiness endpoint returns `ready`.
- [ ] PostgreSQL connectivity is healthy.
- [ ] Redis connectivity is healthy.
- [ ] Frontend loads through its direct service endpoint.
- [ ] Nginx serves frontend and proxies `/api/` correctly.
- [ ] Administrator login and `/auth/me` work.
- [ ] Workflow registry list and BPP detail work.
- [ ] BPP workflow starts and advances through an approved test action.
- [ ] Approval policy evaluation returns the expected level.
- [ ] Snapshots are visible only to authorized users.
- [ ] Notification events are visible and expected delivery statuses are present.
- [ ] Snapshot table growth monitoring is enabled.
- [ ] Failed/queued notification review is assigned to an operator.

## Security Review

- [ ] Default `SECRET_KEY` is absent.
- [ ] Default `BOOTSTRAP_ADMIN_TOKEN` is absent.
- [ ] Bootstrap endpoint requires the secret header.
- [ ] Administrator password was rotated.
- [ ] CORS is restricted to production origins.
- [ ] PostgreSQL password was changed.
- [ ] No secrets or `.env` files are committed.
- [ ] System and BPP role permissions were reviewed.
- [ ] Snapshot endpoints require `snapshots.read`.
- [ ] Notification read/manage/send endpoints require their declared permissions.
- [ ] TLS terminates at the approved ingress or Nginx layer.

## Go-Live Authorization

- [ ] Technical owner approves.
- [ ] Security owner approves.
- [ ] Business workflow owner approves.
- [ ] Backup/rollback owner is available during the release window.
- [ ] Monitoring and support contacts are active.
- [ ] Go-live timestamp and deployed revision are recorded.
