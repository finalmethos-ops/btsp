# BTSP 001P Release Notes

## Release Summary

001P establishes the first production-capable BPP workflow platform and the operational baseline for repeatable on-premises deployment.

## Completed Packages

- 001A: repository, application, container, migration, and validation bootstrap
- 001B: identity, RBAC, and workflow boundaries
- 001C–001D: store authority, batch import, and source adapter foundations
- 001E: immutable event snapshots
- 001F–001G: scoped configuration, change snapshots, and defaults
- 001H–001J: administrator bootstrap, user administration, and permission enforcement
- 001K–001N: authenticated frontend, guarded administration, user management, and configuration UI
- 001O–001O.1: reusable versioned workflow engine and validation hardening
- 001P.1: canonical workflow registry
- 001P.2: BPP purchasing workflow version 1
- 001P.3: configurable approval policy engine
- 001P.4: persistent notification framework
- 001P.5: containerized production validation
- 001P.6: release hardening and deployment readiness
- 001P.7: operational governance and Platform Baseline v1.0 readiness

## Major Capabilities

### Workflow Registry

- Code-owned catalog of deployable workflows
- BPP and Independent workflow separation
- Seed, list, detail, and user-availability APIs
- Active-entry enforcement before workflow use

### BPP Purchasing Workflow

- Versioned `BPP_PURCHASING` definition
- Sixteen states and four terminal outcomes
- Permission-protected happy, revision, rejection, cancellation, and expiration paths
- Exact definition-version retention for running instances

### Approval Policy Engine

- Configuration-backed executive, regional, department, vendor, and category policies
- Deterministic approval ranking
- Safe disabled and incomplete-configuration behavior
- Immutable positive-match snapshots

### Notification Framework

- Persistent templates and notification event history
- In-app, email, and webhook channel contracts
- Six recipient-resolution strategies
- Configurable rendering and immutable emission/failure snapshots

### Administration and Audit

- Controlled initial administrator bootstrap
- Role and permission administration
- Scoped configuration management
- Append-only workflow, policy, configuration, and notification snapshots

## Production Validation Result

001P.5 issued **GO** after:

- Clean Docker Compose build and startup
- PostgreSQL migration through `0008_notification_framework`
- 68 backend tests and Ruff in the Linux container
- Frontend production build and 5 tests in the Node 20 container
- Live health, readiness, bootstrap, authentication, seed, workflow, policy, notification, and snapshot API checks
- Complete authenticated BPP happy path through `completed`
- Live permission and negative-path enforcement

See `docs/validation/001P-production-validation.md`.

## Upgrade Notes

1. Back up PostgreSQL before deployment.
2. Review all environment values and replace development secrets.
3. Build the release images from the intended immutable Git revision.
4. Apply Alembic migrations before accepting traffic.
5. Bootstrap the administrator only when required, then rotate the bootstrap token.
6. Apply registry, platform configuration, BPP, approval, and notification seeds. Seeds are idempotent.
7. Run health, readiness, login, registry, workflow, snapshot, and notification checks.

## Rollback Notes

Database restoration is the preferred rollback mechanism. Alembic downgrades may remove 001P data and should not be used as a substitute for a verified pre-deployment backup. Follow `docs/releases/001P-rollback-plan.md`.

## Known Limitations

- Email delivery is queued through an adapter contract but has no production transport worker.
- Webhook delivery remains disabled by default and uses a stub contract.
- The registry is deployed with application code rather than edited at runtime.
- SSO, refresh tokens, password reset, and account lockout remain future work.
- Production backup scheduling and monitoring must be supplied by the operator.
