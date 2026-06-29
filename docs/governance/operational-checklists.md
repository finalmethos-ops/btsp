# BTSP Operational Governance Checklists

## Checklist Record Standard

Every execution records environment, period, operator, reviewer, start/end time, release SHA, evidence links, findings, risk severity, corrective owner/due date, exceptions, and approval. Checkboxes alone are not sufficient evidence.

## Monthly Permission Review

Owner: Security Owner. Participants: Platform and Operations Owners.

- [ ] Export active/inactive users, roles, permissions, region, and home store.
- [ ] Review every `SYSTEM_ADMIN` assignment and last business justification.
- [ ] Review BPP and Independent roles for workflow separation.
- [ ] Review configuration, store, snapshot, notification, policy, and workflow-action permissions.
- [ ] Identify users with no role, excessive roles, or conflicting scope.
- [ ] Confirm terminated/transferred users are disabled or corrected.
- [ ] Confirm bootstrap token was not reused as an account credential.
- [ ] Record removals/additions through approved administration and audit evidence.
- [ ] Document exceptions and expiration dates.
- [ ] Security Owner signs the review.

## Quarterly Workflow Review

Owner: Workflow Owner. Participants: Architecture, Operations, and Business Owners.

- [ ] Inventory registry entries, definition versions, and lifecycle designation.
- [ ] Confirm only one Production version per workflow code.
- [ ] Confirm retired registrations/definitions cannot start.
- [ ] Reconcile active instances with retained definition versions.
- [ ] Review starts, completion/failure rates, duration, and stale queues.
- [ ] Review transition permissions and role assignments.
- [ ] Review configuration and approval-policy drift.
- [ ] Review notification templates, failures, and recipient strategies.
- [ ] Review snapshot coverage for required workflow/audit events.
- [ ] Confirm deprecation/retirement dates and communications.
- [ ] Validate workflow documentation and owner assignments.
- [ ] Record corrective packages and approvals.

## Configuration Audit

Owner: Platform Owner. Cadence: quarterly and before major release.

- [ ] Export active configuration by scope and key.
- [ ] Confirm owner, business area, environment, default, validation rule, last modification, and reason exist in catalog/change records.
- [ ] Check scoped-key uniqueness and unexpected inactive entries.
- [ ] Compare values to code-owned defaults and approved production deviations.
- [ ] Reconcile updates with `configuration.changed` snapshots.
- [ ] Validate thresholds, allowed values, referenced workflow codes, and dependencies.
- [ ] Confirm test/staging values did not enter production.
- [ ] Test rollback values for high-impact settings.
- [ ] Record unauthorized or unexplained drift as an incident.

## Notification Audit

Owner: Operations Owner. Cadence: monthly.

- [ ] Review active/inactive templates, workflow/event mappings, and channels.
- [ ] Review recipient strategies and static recipient lists for least privilege.
- [ ] Review queued age, sent volume, skipped reasons, and failed events.
- [ ] Reconcile notification events with emitted/failed snapshots.
- [ ] Confirm email/webhook adapters and credentials match approved deployment state.
- [ ] Confirm disabled webhook behavior remains intentional.
- [ ] Sample rendered content for secret or sensitive-data leakage.
- [ ] Record retry/replay decisions and duplicate-delivery risk.

## Snapshot Retention Review

Owner: Data Owner. Cadence: quarterly.

- [ ] Measure snapshot row/storage growth and forecast capacity.
- [ ] Confirm all required event types and trusted actors are represented.
- [ ] Reconcile workflows, approvals, configuration, and notifications with snapshots.
- [ ] Confirm snapshot access is permission-restricted.
- [ ] Review retention, legal hold, archive, encryption, and restore requirements.
- [ ] Test archive/search procedures before deleting any eligible data.
- [ ] Never update historical snapshot rows to perform correction.
- [ ] Record approved retention actions and evidence.

## Database Maintenance

Owner: Database/Operations Owner. Cadence: monthly or managed-service standard.

- [ ] Verify PostgreSQL service/version and Alembic revision.
- [ ] Review storage, table/index growth, connections, locks, and slow queries.
- [ ] Review backup completion, age, checksum, encryption, and off-host copy.
- [ ] Confirm autovacuum/analyze health and maintenance jobs.
- [ ] Review snapshot and notification table growth.
- [ ] Review database errors and recovery/checkpoint warnings.
- [ ] Test credentials and least-privilege network exposure.
- [ ] Schedule disruptive maintenance through change management.

## Dependency Update Review

Owner: Architecture Owner. Cadence: monthly.

- [ ] Review Python, Node, container image, PostgreSQL, Redis, Nginx, and OS advisories.
- [ ] Review framework support windows and end-of-life dates.
- [ ] Update one compatible dependency family at a time where practical.
- [ ] Regenerate lockfiles and review transitive changes.
- [ ] Run security audit, lint, tests, migration, build, and Compose validation.
- [ ] Review release notes for breaking/security behavior.
- [ ] Record deferred vulnerabilities with severity, exposure, owner, and deadline.
- [ ] Update release notes and rollback plan.

## Backup Verification

Owner: Operations Owner. Cadence: monthly; restore quarterly.

- [ ] Confirm scheduled backups completed within RPO.
- [ ] Verify archive size, checksum, encryption, retention, and off-host location.
- [ ] Confirm backup metadata includes release and Alembic revision.
- [ ] Restore into an isolated database using the runbook.
- [ ] Validate core counts, constraints, registry, workflows, configuration, snapshots, and notifications.
- [ ] Measure restore duration against RTO.
- [ ] Remove temporary restored data securely.
- [ ] Record result and corrective actions.

## Disaster Recovery Exercise

Owner: Recovery Owner. Cadence: at least annually.

- [ ] Approve scenario, scope, participants, RTO, and RPO targets.
- [ ] Select a verified backup and matching immutable artifact.
- [ ] Recreate isolated infrastructure, network, storage, secrets, and routing.
- [ ] Restore PostgreSQL and verify Alembic compatibility.
- [ ] Recover configuration, workflows, snapshots, and notification history.
- [ ] Validate admin access, permissions, health, readiness, frontend, and Nginx.
- [ ] Reconcile active workflows and notification replay decisions.
- [ ] Measure detection, decision, restore, validation, and recovery times.
- [ ] Record gaps, owners, due dates, and risk acceptance.
- [ ] Update plans/runbooks and obtain Platform, Security, Operations, and Business sign-off.

## Platform Readiness Checklist

Complete for every major release or baseline:

- [ ] Architecture review passed.
- [ ] Security checklist and access review passed.
- [ ] Performance evidence meets approved targets.
- [ ] Scalability/capacity assessment completed.
- [ ] Maintainability and dependency support reviewed.
- [ ] Backup restore and rollback rehearsal passed.
- [ ] Metrics, logs, alerts, and owners are ready.
- [ ] Documentation links and commands reviewed.
- [ ] Unit, integration, container, and business tests passed.
- [ ] Production-mode deployment and post-deployment checks passed.
- [ ] Release notes, migration notes, rollback, validation, known issues, risk assessment, and approval record complete.
- [ ] Immutable Git tag and image digests recorded after approval.
