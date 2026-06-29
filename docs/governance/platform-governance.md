# BTSP Platform Governance

## Purpose

This policy defines ownership, architecture standards, documentation expectations, and readiness criteria for BTSP as a long-lived enterprise platform.

## Governance Roles

| Role | Accountability |
|---|---|
| Platform Owner | Product direction, service ownership, funding, and final business acceptance |
| Architecture Owner | Platform boundaries, standards, technical debt, and compatibility decisions |
| Security Owner | Security policy, access reviews, exceptions, and incident oversight |
| Workflow Owner | Business definition, configuration, approval policy, and lifecycle of a workflow |
| Data Owner | Store authority, data classification, retention, and recovery requirements |
| Release Manager | Release evidence, approvals, deployment coordination, and rollback readiness |
| Operations Owner | Monitoring, backups, incident response, maintenance, and runbook execution |
| Documentation Owner | Accuracy, review cadence, ownership metadata, and obsolete-document retirement |

One person may hold multiple roles in a small installation, but each accountability must be explicitly assigned.

## Platform Administration

- Administrative access uses named accounts; shared administrator accounts are prohibited.
- `SYSTEM_ADMIN` assignment requires Platform and Security Owner approval.
- Routine workflow administration uses the narrowest workflow-specific role.
- Administrative actions must be attributable through authentication, application records, snapshots, and container/platform logs.
- Bootstrap credentials are installation-only and must be rotated after first use.
- Production configuration and seed execution follow change management and leave auditable evidence.

## Architecture Standards

### Configuration over Code

Variable business behavior belongs in validated, scoped configuration. Code defines contracts, safe defaults, and invariants. A configuration change must identify owner, reason, validation, approver, and rollback value.

### Immutable Event Snapshots

Snapshots are append-only evidence. Corrections create new records; operators do not edit historical rows. Access requires explicit permission, and retention preserves regulatory and incident-response needs.

### Workflow Versioning

Definitions are immutable by version after production approval. Running instances retain their recorded definition version. New behavior uses a new version and follows the workflow lifecycle policy.

### Role-Based Access Control

Routes declare explicit permissions. Roles bundle permissions by job responsibility and workflow boundary. Frontend visibility is advisory; backend authorization is authoritative.

### Single Source of Truth

- Official Store Database controls store identity and organizational scope.
- PostgreSQL controls application state.
- Code-owned workflow registry controls deployable workflow capabilities.
- Versioned workflow definitions control runtime transitions.
- Scoped configuration controls variable business policy.

Parallel editable catalogs are prohibited unless an approved synchronization contract exists.

### API Versioning

Public APIs remain under `/api/v1` until a reviewed incompatible contract requires a new major API namespace. Additive fields and endpoints are preferred.

### Backward Compatibility

- Existing clients must tolerate additive response fields.
- Removing fields, permissions, states, routes, or configuration keys requires migration and deprecation plans.
- Running workflow instances must remain executable on their pinned definitions.
- Database changes are forward migrations with documented rollback limitations.

### Database Migration Strategy

- Every schema change uses an ordered Alembic revision.
- Revision identifiers fit the Alembic version column.
- Migrations run against a disposable PostgreSQL copy before production.
- A verified backup is mandatory before migration.
- Destructive downgrades are not the primary rollback mechanism; restore is preferred.

### Documentation Requirements

Every package records objective, scope, API/schema changes, architecture effects, validation, rollback considerations, and known limitations. Operationally material behavior requires an architecture note or runbook update.

### Testing Standards

- Unit tests cover deterministic contracts and negative paths.
- Database-backed integration tests cover persistence, uniqueness, permissions, snapshots, and idempotency.
- Workflow releases cover complete happy and terminal paths.
- Container validation uses the supported Python, Node, PostgreSQL, and Redis versions.
- Security-sensitive actor and permission behavior is tested at the service/API boundary.

## Configuration Governance

Every governed configuration item must have the following metadata in its catalog or approved change record:

| Metadata | Requirement |
|---|---|
| Owner | Named business or platform owner |
| Business Area | Domain accountable for behavior |
| Environment | Development, test, staging, or production |
| Default Value | Code-owned starter value and representation |
| Validation Rules | Type, range, allowed values, and dependencies |
| Last Modified | UTC timestamp and actor from persisted entry/snapshot |
| Change Reason | Ticket, incident, policy, or release justification |

Current configuration rows persist scope, key, value, actor, and timestamps. Owner, environment, default, validation, and reason are maintained in release/configuration documentation and the approved change record until dedicated metadata fields are introduced.

Configuration changes require:

1. Proposed before/after values and affected scopes.
2. Validation and impact analysis.
3. Workflow and business-owner approval where applicable.
4. Tested rollback value.
5. Production execution by an authorized user.
6. Snapshot and post-change verification.

## Documentation Governance

- Each document has a clear subject, scope, and owning governance role.
- Package documentation is immutable release history; corrections are committed with explanation.
- Runbooks are tested at least annually and after material platform changes.
- Governance policies are reviewed at least annually.
- Broken links, stale commands, unsupported versions, and superseded procedures are release blockers.
- Retired documents remain in version control and point readers to their replacement.

## Platform Readiness Review

Each release is reviewed across:

- Architecture
- Security
- Performance
- Scalability
- Maintainability
- Recoverability
- Observability
- Documentation
- Testing
- Deployment

The Release Manager records pass, conditional pass, or fail for each area, evidence links, accepted risks, approvers, and expiration dates for exceptions.

## Release Governance

Every release includes:

- Release notes
- Migration notes
- Rollback instructions
- Validation report
- Known issues
- Risk assessment
- Approval record
- Completed platform-readiness checklist

An approval record contains release identifier and Git SHA, artifact/image identifiers, environment, validation report, risk owners, Platform/Security/Operations/Business approvals, approval timestamps, deployment window, and rollback owner.

No release is production-approved solely because automated tests pass. Required human approvals must be recorded; absent approval remains a release blocker.

## Exceptions

Exceptions document the violated standard, justification, risk, compensating control, owner, approver, expiration date, and remediation package. Permanent undocumented exceptions are prohibited.
