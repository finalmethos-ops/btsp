# BPP Purchasing Workflow — Version 1

## Metadata

- Code: `BPP_PURCHASING`
- Version: `1`
- Business area: Purchasing
- Category: BPP Ordering
- Configuration namespace: `workflow.bpp_purchasing`
- Initial state: `draft`
- Terminal states: `completed`, `rejected`, `cancelled`, `expired`

## States

1. `draft`
2. `department_review`
3. `purchasing_review`
4. `vendor_selection`
5. `cost_verification`
6. `executive_approval`
7. `po_created`
8. `vendor_submission`
9. `vendor_confirmed`
10. `shipment_scheduled`
11. `receiving`
12. `completed`
13. `revision_requested`
14. `rejected`
15. `cancelled`
16. `expired`

## Transition and Permission Matrix

| Action | From | To | Required permission |
|---|---|---|---|
| `submit_for_department_review` | `draft` | `department_review` | `workflow.bpp.submit` |
| `department_approve` | `department_review` | `purchasing_review` | `workflow.bpp.department_review` |
| `return_for_revision` | `department_review` | `revision_requested` | `workflow.bpp.revise` |
| `return_for_revision` | `purchasing_review` | `revision_requested` | `workflow.bpp.revise` |
| `return_for_revision` | `vendor_selection` | `revision_requested` | `workflow.bpp.revise` |
| `return_for_revision` | `cost_verification` | `revision_requested` | `workflow.bpp.revise` |
| `return_for_revision` | `executive_approval` | `revision_requested` | `workflow.bpp.revise` |
| `resubmit` | `revision_requested` | `department_review` | `workflow.bpp.revise` |
| `purchasing_approve` | `purchasing_review` | `vendor_selection` | `workflow.bpp.purchasing_review` |
| `select_vendor` | `vendor_selection` | `cost_verification` | `workflow.bpp.vendor_select` |
| `verify_cost` | `cost_verification` | `executive_approval` | `workflow.bpp.cost_verify` |
| `executive_approve` | `executive_approval` | `po_created` | `workflow.bpp.executive_approve` |
| `generate_po` | `po_created` | `vendor_submission` | `workflow.bpp.po_generate` |
| `submit_to_vendor` | `vendor_submission` | `vendor_confirmed` | `workflow.bpp.vendor_submit` |
| `confirm_vendor` | `vendor_confirmed` | `shipment_scheduled` | `workflow.bpp.vendor_confirm` |
| `schedule_shipment` | `shipment_scheduled` | `receiving` | `workflow.bpp.shipment_schedule` |
| `receive_order` | `receiving` | `completed` | `workflow.bpp.receive` |
| `reject` | `department_review` | `rejected` | `workflow.bpp.reject` |
| `reject` | `purchasing_review` | `rejected` | `workflow.bpp.reject` |
| `reject` | `executive_approval` | `rejected` | `workflow.bpp.reject` |
| `cancel` | `draft` | `cancelled` | `workflow.bpp.cancel` |
| `cancel` | `revision_requested` | `cancelled` | `workflow.bpp.cancel` |
| `expire` | `department_review` | `expired` | `workflow.bpp.expire` |
| `expire` | `purchasing_review` | `expired` | `workflow.bpp.expire` |
| `expire` | `executive_approval` | `expired` | `workflow.bpp.expire` |

## Permission Catalog

- `workflow.bpp.submit`
- `workflow.bpp.department_review`
- `workflow.bpp.purchasing_review`
- `workflow.bpp.vendor_select`
- `workflow.bpp.cost_verify`
- `workflow.bpp.executive_approve`
- `workflow.bpp.po_generate`
- `workflow.bpp.vendor_submit`
- `workflow.bpp.vendor_confirm`
- `workflow.bpp.shipment_schedule`
- `workflow.bpp.receive`
- `workflow.bpp.revise`
- `workflow.bpp.reject`
- `workflow.bpp.cancel`
- `workflow.bpp.expire`

## Configuration Defaults

All entries use scope type `workflow` and scope key `BPP_PURCHASING`.

| Key | Stored value |
|---|---|
| `enabled` | `{"enabled": true}` |
| `executive_approval_threshold` | `{"amount": 50000}` |
| `auto_approval_enabled` | `{"enabled": false}` |
| `allow_revision` | `{"enabled": true}` |
| `allow_cancel_from_draft` | `{"enabled": true}` |
| `notification_enabled` | `{"enabled": true}` |

## Seed Instructions

Apply migrations, authenticate as a user with `configuration.manage`, then call:

```bash
curl -X POST http://localhost:8000/api/v1/workflow-engine/seeds/bpp-purchasing \
  -H "Authorization: Bearer $BTSP_ACCESS_TOKEN"
```

The seed is repeatable. It updates the permission catalog, role permission assignments, version 1 definition, and configuration defaults without duplicating those records.

## Validation

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```
