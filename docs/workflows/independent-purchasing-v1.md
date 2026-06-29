# Independent Purchasing Workflow — Version 1

## Metadata

- Workflow code: `IND_PURCHASING`
- Display name: Independent Purchasing
- Version: 1
- Business area: Purchasing
- Category: Independent Ordering
- Configuration namespace: `workflow.ind_purchasing`
- Registry lifecycle: Testing
- Initial state: `draft`
- Terminal states: `completed`, `rejected`, `cancelled`, `expired`

Production promotion follows `docs/governance/workflow-governance.md` and requires recorded staging/business approval.

## Architecture

Independent Purchasing reuses the shared workflow engine, registry, approval evaluator, notification service, configuration service, identity/RBAC, store authority, and snapshots. It does not share BPP definitions, roles, permissions, configuration scope, templates, or business transitions.

At API start, the authenticated user must hold `workflow.ind.submit`, have a region, and submit an active/orderable Official Store Database store within that region.

## State Diagram

```text
draft → store_review → franchise_review → vendor_selection
      → pricing_review → regional_approval → po_created
      → vendor_submission → vendor_acknowledged
      → shipment_scheduled → receiving → completed

review states → revision_requested → store_review
review states → rejected
draft/revision_requested → cancelled
review states → expired
rejected/cancelled/expired --administrative_reopen→ draft
```

## States

1. `draft`
2. `store_review`
3. `franchise_review`
4. `vendor_selection`
5. `pricing_review`
6. `regional_approval`
7. `po_created`
8. `vendor_submission`
9. `vendor_acknowledged`
10. `shipment_scheduled`
11. `receiving`
12. `completed`
13. `revision_requested`
14. `rejected`
15. `cancelled`
16. `expired`

## Transition and Permission Matrix

| Action | From | To | Permission |
|---|---|---|---|
| `submit_for_store_review` | `draft` | `store_review` | `workflow.ind.submit` |
| `store_approve` | `store_review` | `franchise_review` | `workflow.ind.review` |
| `franchise_approve` | `franchise_review` | `vendor_selection` | `workflow.ind.franchise_approve` |
| `select_vendor` | `vendor_selection` | `pricing_review` | `workflow.ind.vendor_select` |
| `verify_pricing` | `pricing_review` | `regional_approval` | `workflow.ind.review` |
| `regional_approve` | `regional_approval` | `po_created` | `workflow.ind.regional_approve` |
| `generate_po` | `po_created` | `vendor_submission` | `workflow.ind.review` |
| `submit_to_vendor` | `vendor_submission` | `vendor_acknowledged` | `workflow.ind.review` |
| `acknowledge_vendor` | `vendor_acknowledged` | `shipment_scheduled` | `workflow.ind.receive` |
| `schedule_shipment` | `shipment_scheduled` | `receiving` | `workflow.ind.receive` |
| `receive_order` | `receiving` | `completed` | `workflow.ind.receive` |
| `return_for_revision` | `store_review`, `franchise_review`, `vendor_selection`, `pricing_review`, `regional_approval` | `revision_requested` | `workflow.ind.review` |
| `resubmit` | `revision_requested` | `store_review` | `workflow.ind.submit` |
| `reject` | `store_review`, `franchise_review`, `regional_approval` | `rejected` | `workflow.ind.reject` |
| `cancel` | `draft`, `revision_requested` | `cancelled` | `workflow.ind.cancel` |
| `expire` | `store_review`, `franchise_review`, `regional_approval` | `expired` | `workflow.ind.review` |
| `administrative_reopen` | `rejected`, `cancelled`, `expired` | `draft` | `system.admin` |

Completed instances remain locked and cannot be reopened.

## Permission Matrix

| Permission | Responsibility |
|---|---|
| `workflow.ind.submit` | Start and submit Independent requests |
| `workflow.ind.review` | Store/pricing review, revision, PO/vendor processing, expiration |
| `workflow.ind.franchise_approve` | Franchise approval |
| `workflow.ind.regional_approve` | Regional approval |
| `workflow.ind.vendor_select` | Vendor selection |
| `workflow.ind.receive` | Vendor acknowledgment, shipment scheduling, receiving |
| `workflow.ind.cancel` | Cancellation |
| `workflow.ind.reject` | Rejection |

`INDEPENDENT_ADMIN` receives these permissions. Administrative reopen remains a system-administrator action.

## Approval Policies

| Policy | Default behavior | Level |
|---|---|---|
| Store default | Every enabled request | Store |
| Regional dollar threshold | Amount at least 25000 | Regional |
| Franchise spending limit | Amount at least 10000 | Franchise |
| Store credit limit | Amount at least configured/context store limit | Franchise |
| Vendor restriction | Vendor in configured list | Franchise |
| Restricted categories | Category in configured list | Franchise |
| Regional override | Context `regional_override=true` | Executive/system admin |

Ranking is executive, regional, franchise, then store. Thresholds and lists are database configuration and can change without code deployment.

## Notification Catalog

Nine active in-app templates are seeded for submission, approval, revision, rejection, PO creation, vendor submission, vendor acknowledgment, receiving, and completion. Email uses the shared queued adapter contract. Webhook remains skipped unless enabled by workflow configuration.

## Configuration Reference

All entries use scope type `workflow` and scope key `IND_PURCHASING`.

### Workflow Defaults

- `enabled`: `{"enabled": true}`
- `regional_threshold`: `{"amount": 25000}`
- `franchise_threshold`: `{"amount": 10000}`
- `allow_revision`: `{"enabled": true}`
- `allow_cancel`: `{"enabled": true}`
- `notification.enabled`: `{"enabled": true}`
- `notification.channels`: `{"channels": ["in_app", "email"]}`

### Approval Defaults

- `approval.enabled`
- `approval.store_default`
- `approval.regional_threshold`
- `approval.franchise_spending_limit`
- `approval.store_credit_limit`
- `approval.restricted_vendors`
- `approval.restricted_categories`
- `approval.regional_override`

## API Reference

- `POST /api/v1/workflow-engine/seeds/ind-purchasing`
- `POST /api/v1/workflow-engine/instances`
- `POST /api/v1/workflow-engine/instances/{instance_id}/actions`
- `POST /api/v1/approval-policies/evaluate`
- `POST /api/v1/notifications/emit`
- `GET /api/v1/notifications/events`
- `GET /api/v1/snapshots`
- `GET /api/v1/workflow-registry/IND_PURCHASING`

## Validation

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml build
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend pytest
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend ruff check app tests
docker compose -f docker-compose.yml -f docker-compose.production.yml exec frontend npm run build
docker compose -f docker-compose.yml -f docker-compose.production.yml exec frontend npm test -- --run
```

## Acceptance Criteria

- Registry metadata and Testing lifecycle are correct.
- Installer is idempotent.
- Happy path reaches `completed`.
- Approval configuration changes alter evaluated level.
- Notifications emit through the shared framework.
- Every workflow action produces a snapshot.
- Permissions, region/store authority, invalid transitions, and completed lock are enforced.
- BPP behavior and artifacts remain separate and passing.
