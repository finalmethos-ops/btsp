# BTSP Workflow Governance

## Purpose

This policy governs workflow design, versioning, promotion, deprecation, retirement, and production ownership.

## Lifecycle States

| State | Meaning | Permitted activity |
|---|---|---|
| Draft | Initial design under active change | Definition editing and local review only |
| Testing | Automated and integration validation | Test data and non-production execution |
| Staging | Release-candidate business validation | Production-like data controls and acceptance testing |
| Production | Approved version available for new instances | Controlled production execution |
| Deprecated | Still readable/executable for compatibility; replacement announced | No new feature development; starts allowed only by approved sunset policy |
| Retired | Historical definition retained, unavailable for new instances | Read/audit and completion policy only |

Lifecycle state is a governance designation currently recorded in the workflow catalog/release approval. Runtime `is_active=false` enforces that a retired registration or definition cannot be selected for new instances.

## Mandatory Rules

1. Only one workflow definition version per workflow code may hold Production designation.
2. Version history is retained in the database, source, release notes, and snapshots.
3. Production definitions are not edited in place; behavior changes create a new version.
4. Existing instances continue on their pinned definition version.
5. Deprecated definitions remain readable for audit and compatible instance handling.
6. Retired workflows have inactive registry/definition status and cannot be started.
7. BPP and Independent workflows retain separate definitions, permissions, configuration, reports, and audit records.
8. Terminal states and correction behavior are explicitly documented.

## Promotion Gates

### Draft to Testing

- Workflow owner and definition are identified.
- State and transition matrices are complete.
- Permissions, configuration, policy, notifications, snapshots, and failure behavior are specified.
- Unit tests cover every transition and terminal condition.

### Testing to Staging

- Automated tests and migrations pass.
- Seed is idempotent.
- Security and permission review passes.
- Upgrade and rollback effects are documented.
- Test evidence and known issues are attached.

### Staging to Production

- Business owner completes scenario acceptance.
- Production-like performance and operational checks pass.
- Backup, deployment, monitoring, and rollback owners are ready.
- Release approval record is complete.
- Exactly one version is designated Production.

### Production to Deprecated

- Replacement or retirement rationale is approved.
- New-start policy and sunset date are published.
- Running instance inventory and compatibility are assessed.
- Users and report owners are notified.

### Deprecated to Retired

- No unhandled active instances remain, or an approved completion/migration plan exists.
- Registration and definition are inactive for starts.
- Read/audit paths are validated.
- Configuration and notification ownership is archived.

## Version Review Record

Every promoted version records:

- Workflow code, name, and version
- Current and target lifecycle states
- Business and technical owners
- Definition checksum or immutable Git SHA
- State/transition and permission matrix links
- Configuration namespace/defaults
- Approval and notification behavior
- Migration/seed version and idempotency evidence
- Test and staging validation evidence
- Compatibility and rollback assessment
- Approvers and timestamps

## Production Invariants

- Registry entry and active definition metadata agree.
- The designated production version is unique.
- Required permissions exist and role assignments are reviewed.
- Required configuration is active and valid.
- Running instances reference existing retained versions.
- Snapshots capture start, advance, terminal, and policy events.
- Notification failures cannot silently mutate workflow state.

## Quarterly Workflow Review

The Workflow Owner and Operations Owner perform the procedure in `operational-checklists.md`, including version inventory, active/terminal instance counts, failure rate, stale instances, permission assignments, configuration drift, notification failures, snapshot coverage, deprecation dates, and documentation accuracy.

## Emergency Changes

Emergency workflow changes still require a new version unless correcting an unreleased definition. Record incident, risk, approver, exact change, validation performed, rollback plan, and retrospective review date. Emergency status does not authorize deleting version history.
