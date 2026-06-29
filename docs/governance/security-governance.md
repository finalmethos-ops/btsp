# BTSP Security Governance

## Purpose

This policy defines recurring access, identity, secret, session, and operational security controls for BTSP.

## Security Ownership

The Security Owner approves policy, exceptions, high-privilege access, and incident actions. The Platform Owner owns remediation. Operations executes recurring reviews. Evidence is retained with the release or access-review record.

## Access Principles

- Named accounts only; no shared administrator credentials.
- Least privilege and workflow separation.
- Backend permission enforcement is authoritative.
- Dormant access is removed promptly.
- Administrative and audit data is accessible only through declared permissions.
- Production data and secrets are never copied into development without approval and sanitization.

## Required Reviews

### Monthly Role and Permission Audit

- Export users, roles, permissions, active status, regions, and stores.
- Compare assignments to approved job responsibilities.
- Review `SYSTEM_ADMIN`, `BPP_ADMIN`, workflow action, policy, notification, configuration, snapshot, and store permissions.
- Remove excessive, orphaned, duplicate, or conflicting access.
- Record reviewer, date, changes, exceptions, and next review.

### Inactive User Review

- Identify users exceeding the organization's inactivity threshold.
- Confirm employment/contract status with the account owner.
- Disable stale accounts; do not delete audit identity.
- Investigate activity after termination or unexpected region/store changes.

### Administrative Account Review

- Review all system administrators monthly.
- Confirm named owner, business need, MFA/host control where available, and last use.
- Maintain at least one tested emergency recovery path under dual control.

### API Key and Integration Credential Review

BTSP currently uses JWTs and bootstrap/environment secrets rather than managed API keys. Review any future email, webhook, store-source, SSO, or service credentials quarterly and after personnel/vendor changes.

## Secret Rotation Schedule

| Secret | Minimum rotation |
|---|---|
| Bootstrap token | Immediately after bootstrap and after any suspected exposure |
| JWT `SECRET_KEY` | At least annually and after exposure; plan active-session invalidation |
| PostgreSQL password | Per organizational standard, at least annually |
| Redis credential/connection secret | Per organizational standard, at least annually |
| External delivery/integration secret | At least every 90 days or provider policy |

Rotations require a change record, coordinated container recreation, health checks, and rollback values. Secrets never appear in tickets, logs, snapshots, commits, or screenshots.

## Password Policy

- Initial administrator/user passwords are temporary and changed before normal use.
- Use organizational minimum length and compromised-password controls; until centrally enforced, administrators apply policy operationally.
- Passwords are hashed with salted PBKDF2; plaintext storage or transmission outside TLS is prohibited.
- Password reset and lockout are known future capabilities and require compensating operational procedures.

## Session Expiration Policy

- `ACCESS_TOKEN_EXPIRE_MINUTES` is risk-approved and as short as practical.
- Production uses HTTPS only.
- Secret-key rotation invalidates outstanding JWTs and requires a communications plan.
- Shared/public workstations are not approved for administrative sessions.
- Refresh tokens are not currently supported.

## Production Security Checklist

- [ ] Default `SECRET_KEY` removed.
- [ ] Default `BOOTSTRAP_ADMIN_TOKEN` removed and post-bootstrap token rotated.
- [ ] Bootstrap endpoint requires the secret header and is network-restricted.
- [ ] Initial administrator password changed.
- [ ] CORS restricted to approved HTTPS origins.
- [ ] PostgreSQL password changed from local default.
- [ ] Redis is not publicly exposed and uses approved protections.
- [ ] `.env`, dumps, tokens, and private keys are absent from Git.
- [ ] Role and permission assignments reviewed.
- [ ] Inactive users and administrative accounts reviewed.
- [ ] Snapshot access requires `snapshots.read`.
- [ ] Notification access requires read/manage/send permissions.
- [ ] Configuration writes require `configuration.manage`.
- [ ] TLS and security headers are verified at ingress.
- [ ] Backup encryption and access controls are verified.
- [ ] Logs and snapshots contain no credentials or secret payloads.

## Security Events and Response

Preserve authentication, permission, administrative, configuration, workflow, notification, infrastructure, and proxy evidence. On suspected compromise:

1. Activate the incident process.
2. Contain affected accounts/services.
3. Preserve logs, snapshots, database state, and timestamps.
4. Rotate affected secrets and terminate access.
5. Validate data/workflow integrity.
6. Restore or redeploy from trusted artifacts when required.
7. Record root cause, impact, notification obligations, and remediation.

## Exceptions

Security exceptions require Security Owner approval, business justification, compensating controls, accountable owner, expiration date, and tracked remediation. Expired exceptions block release approval.
