# BTSP 001P Known Issues

## Open Limitations

| Area | Limitation | Operational treatment |
|---|---|---|
| Email | Events queue, but no production email worker is included | Keep email disabled unless a supported worker is deployed; monitor queued events |
| Webhooks | Adapter is a stub and disabled by default | Leave `notification.webhook_enabled` false |
| Authentication | JWTs use browser local storage and there are no refresh tokens | Use HTTPS, short expirations, restricted origins, and controlled workstations |
| Identity lifecycle | No SSO, password reset, or account lockout | Use administrator-managed accounts and local access procedures |
| Bootstrap | Endpoint remains deployed after first use | Rotate `BOOTSTRAP_ADMIN_TOKEN` and restrict network access |
| Registry | Workflow registrations are code-owned | Deliver additions through reviewed release packages |
| Backups | No bundled scheduler or off-host target | Configure operator-owned encrypted, monitored backups |
| Observability | Application logs are container stdout/stderr without centralized aggregation | Collect Docker logs with the site's approved logging platform |
| Compose modes | Base Compose runs development servers and bind mounts | Production must include `docker-compose.production.yml` |
| Secrets | Compose consumes a local `.env` file | Protect host permissions; never commit `.env`; prefer a secret manager when available |

## Accepted Design Constraints

- PostgreSQL is the system of record.
- Redis availability is required for readiness even though asynchronous delivery is not yet implemented.
- Snapshots are append-only and can grow continuously; retention and archival require operational policy.
- BPP and Independent workflows remain separate across registry, permission, configuration, and reporting boundaries.

## Release-Candidate Hygiene

The production validation report may reference a dirty development worktree. A deployment artifact must be built from a reviewed, committed, immutable revision and tagged according to the operator's release process.

## Reporting New Issues

Record the affected release, timestamp, environment, API route or workflow instance, relevant container logs, and snapshot/entity identifiers. Do not include passwords, tokens, database URLs, or message secrets in issue records.
