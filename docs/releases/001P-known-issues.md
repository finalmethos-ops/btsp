# BTSP 001P Known Issues

## Open Limitations

| Area | Limitation | Operational treatment |
|---|---|---|
| Email | SMTP delivery is synchronous and production SMTP is not configured | Keep email disabled until an approved SMTP service is configured; monitor queued events and failed deliveries |
| Webhooks | HTTPS delivery is implemented but disabled in production and no approved destination is configured | Leave `notification.webhook_enabled` false until destinations and retry/incident procedures are approved |
| Authentication | Access and refresh tokens use per-tab browser session storage rather than HttpOnly cookies | Continue enforcing HTTPS, short access-token lifetimes, refresh-session revocation, a restrictive CSP, explicit origins, and reviewed frontend dependencies |
| Identity lifecycle | Password reset, login throttling, and timed account lockout are available, but SSO is not implemented | Use administrator-managed accounts and the audited password-reset flow; evaluate corporate SSO before broader external rollout |
| Registry | Workflow registrations are code-owned | Deliver additions through reviewed release packages |
| Backups | Encrypted scheduled backups and verified Cloudflare R2 copies are configured on the current production host, but recovery still depends on that host's operator-owned task and credentials | Monitor the scheduled task, R2 verification, archive age, and periodic disposable restore results |
| Observability | A scheduled production watchdog, bounded local event log, container log rotation, and optional alert webhook are available; centralized log aggregation is not configured | Keep the watchdog task healthy and connect its webhook and Docker logs to the site's approved monitoring platform when available |
| Compose modes | Base Compose runs development servers and bind mounts | Production must include `docker-compose.production.yml` |
| Secrets | Compose consumes protected local environment and runtime-secret files | Preserve the audited Windows ACLs and rotation ledger; never commit secret files; prefer a managed secret store when available |

## Accepted Design Constraints

- PostgreSQL is the system of record.
- Redis availability is required for readiness even though asynchronous delivery is not yet implemented.
- Snapshots are append-only and can grow continuously; retention and archival require operational policy.
- BPP and Independent workflows remain separate across registry, permission, configuration, and reporting boundaries.

## Release-Candidate Hygiene

The production validation report may reference a dirty development worktree. A deployment artifact must be built from a reviewed, committed, immutable revision and tagged according to the operator's release process.

## Reporting New Issues

Record the affected release, timestamp, environment, API route or workflow instance, relevant container logs, and snapshot/entity identifiers. Do not include passwords, tokens, database URLs, or message secrets in issue records.
