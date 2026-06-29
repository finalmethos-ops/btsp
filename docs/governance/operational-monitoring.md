# BTSP Operational Monitoring and Audit Standards

## Purpose

Define the minimum health, performance, workflow, audit, capacity, and notification signals required to operate BTSP safely.

## Monitoring Ownership

The Operations Owner maintains collection, dashboards, alert routing, retention, and response runbooks. Workflow Owners review business-flow metrics. Security reviews access/audit signals. Thresholds are environment-specific, approved, tested, and recorded in the monitoring platform.

## Required Metrics

| Metric | Definition | Primary source |
|---|---|---|
| Workflow instances started | Count of `workflow.started` by code/version | Event snapshots / workflow instances |
| Workflow completion rate | Completed instances divided by terminal instances in period | Workflow instances |
| Workflow failure rate | Rejected, cancelled, expired, or operationally failed instances divided by started | Workflow instances and snapshots |
| Average workflow duration | Mean `updated_at - started_at` for terminal instances | Workflow instances |
| Approval queue size | Active instances in configured approval states | Workflow instances |
| Notification success rate | Sent events divided by delivery-attempt events | Notification events |
| Notification failure rate | Failed events divided by delivery-attempt events | Notification events |
| Snapshot growth | Rows and storage growth per day/week | PostgreSQL statistics / event snapshots |
| API response times | Request count and latency percentiles by route/status | Nginx/backend telemetry |
| Database connection health | Readiness probe, connection errors, pool saturation | Backend and PostgreSQL |
| Redis availability | Ping/readiness success and connection errors | Backend readiness and Redis |

At minimum, dashboards segment workflows by code/version and notifications by channel/status. Do not put entity payloads, credentials, or personal data into metric labels.

## Minimum Alerts

- Health or readiness failure
- Container restart loop or unavailable service
- PostgreSQL or Redis connection failure
- API 5xx rate or latency above approved threshold
- Workflow completion-rate degradation or stale approval queue
- Notification failure-rate increase or growing queued backlog
- Snapshot/database storage approaching capacity
- Backup failure, stale backup, or failed restore exercise
- Repeated authentication/authorization failures
- Migration mismatch from approved Alembic head

Every alert has severity, owner, runbook, acknowledgment target, escalation path, and maintenance-window behavior.

## Health and Readiness

- `/api/v1/health` proves the application process responds.
- `/api/v1/ready` proves PostgreSQL and Redis connectivity.
- Nginx checks prove frontend routing and `/api/` proxying.
- Health checks do not replace business transaction monitoring.

## Log Standards

- Services log to stdout/stderr for collection by the container platform.
- Production timestamps use UTC and retain service/container identity.
- Errors include safe correlation/entity identifiers, not secrets or entire sensitive payloads.
- Tracebacks, migration failures, authentication anomalies, notification failures, database recovery, and proxy upstream errors are searchable.
- Retention and access follow security and regulatory policy.

Current BTSP logging is framework/container oriented and lacks structured request correlation. Central aggregation, request IDs, and metrics instrumentation are platform follow-up work and must be tracked as observability debt.

## Audit Event Standard

| Required event | Canonical event type | Current evidence |
|---|---|---|
| Workflow started | `workflow.started` | Implemented snapshot |
| Workflow advanced | `workflow.advanced` | Implemented snapshot |
| Workflow cancelled | `workflow.cancelled` or terminal `workflow.advanced` | Terminal transition currently evidenced by `workflow.advanced`; dedicated producer recommended |
| Workflow rejected | `workflow.rejected` or terminal `workflow.advanced` | Terminal transition currently evidenced by `workflow.advanced`; dedicated producer recommended |
| Workflow completed | `workflow.completed` or terminal `workflow.advanced` | Terminal transition currently evidenced by `workflow.advanced`; dedicated producer recommended |
| Approval evaluated | `approval.policy.matched` | Positive match implemented; disabled/no-match decision audit is future policy |
| Configuration changed | `configuration.changed` | Implemented snapshot |
| Permission changed | `permission.changed` | Required; dedicated producer not yet implemented |
| Notification emitted | `notification.emitted` | Implemented snapshot |
| Notification failed | `notification.failed` | Implemented snapshot |
| User login | `user.login` | Required; dedicated producer not yet implemented |
| Administrative action | `administrative.action` | Required; specific user/config actions partially evidenced, unified producer pending |

Audit gaps are not silently treated as implemented. Release risk assessments identify them, and future packages add dedicated producers without rewriting historical snapshots.

## Audit Record Requirements

- UTC timestamp
- Trusted actor
- Event type
- Entity type and immutable identifier
- Workflow code/version when applicable
- Outcome and relevant before/after state
- Concise non-secret payload
- Correlation identifier when available

Snapshots remain append-only. Corrections create a new event referencing the corrected entity/event.

## Daily Operations Review

- Confirm all services healthy and current Alembic revision expected.
- Review error/restart and database/Redis connection signals.
- Review failed and aging queued notifications.
- Review stale active workflow/approval instances.
- Confirm most recent backup succeeded.
- Review capacity trends for PostgreSQL, snapshots, and Docker storage.

## Monthly and Quarterly Review

Execute the recurring procedures in `docs/governance/operational-checklists.md`. Attach dashboard exports, query results, findings, owners, due dates, and approvals to the operational review record.

## Data Quality and Reconciliation

Periodically reconcile:

- Instance starts against `workflow.started` snapshots
- Terminal instances against terminal transition snapshots
- Positive approval results against `approval.policy.matched`
- Notification events against emitted/failed snapshots
- Configuration updated timestamps against change snapshots

Unexplained mismatch is an incident or defect, not an acceptable monitoring variance.
