# BPP Approval Policies — Version 1

## Purpose

The BPP approval policy engine evaluates purchasing requests against database-backed configuration. It selects the highest required approval without embedding monetary, vendor, or category policy in workflow transitions.

Configuration namespace: `workflow.bpp_purchasing.approvals`

## Policy Input Contract

| Field | Type | Required |
|---|---|---|
| `workflow_code` | string | yes |
| `entity_type` | string | yes |
| `entity_id` | string | yes |
| `request_amount` | non-negative decimal | yes |
| `region_code` | string or null | no |
| `store_number` | string or null | no |
| `vendor_code` | string or null | no |
| `product_category` | string or null | no |
| `buying_group_code` | string or null | no |
| `submitted_by` | string | yes |
| `context` | JSON object | yes, defaults to `{}` |

The API replaces `submitted_by` with the authenticated user's email before evaluation. Direct service callers must provide the trusted actor explicitly.

## Policy Output Contract

| Field | Type |
|---|---|
| `requires_approval` | boolean |
| `approval_level` | approval-level code |
| `approval_reason` | string or null |
| `required_permission` | string or null |
| `routing_group` | string or null |
| `matched_policy_codes` | ordered string list |

Matched policies are returned from highest to lowest approval rank.

## Approval Level Ranking

Highest priority first:

1. `system_admin`
2. `executive`
3. `regional`
4. `purchasing`
5. `department`
6. `none`

Executive approval therefore outranks regional approval when both thresholds match.

## Default Policy Catalog

| Policy code | Match | Result | Permission |
|---|---|---|---|
| `executive_threshold` | Amount is at least 50000 | `executive` | `workflow.bpp.executive_approve` |
| `regional_threshold` | Amount is at least 25000 | `regional` | `workflow.bpp.regional_approve` |
| `department_default` | Enabled BPP request | `department` | `workflow.bpp.department_review` |
| `vendor_restricted` | Vendor is configured as restricted | `purchasing` | `workflow.bpp.purchasing_review` |
| `category_restricted` | Category is configured as restricted | `purchasing` | `workflow.bpp.purchasing_review` |

## Routing Groups

| Approval level | Routing group |
|---|---|
| `department` | `bpp.department_approvers` |
| `purchasing` | `bpp.purchasing_approvers` |
| `regional` | `bpp.regional_approvers` |
| `executive` | `bpp.executive_approvers` |
| `system_admin` | `system.administrators` |

## Configuration Reference

All entries use scope type `workflow` and scope key `BPP_PURCHASING`.

| Key | Default value |
|---|---|
| `approval.enabled` | `{"enabled": true}` |
| `approval.executive_threshold` | `{"amount": 50000, "approval_level": "executive", "required_permission": "workflow.bpp.executive_approve"}` |
| `approval.regional_threshold` | `{"amount": 25000, "approval_level": "regional", "required_permission": "workflow.bpp.regional_approve"}` |
| `approval.department_default` | `{"approval_level": "department", "required_permission": "workflow.bpp.department_review"}` |
| `approval.restricted_vendors` | `{"vendor_codes": []}` |
| `approval.restricted_categories` | `{"product_categories": []}` |

When approval is enabled, missing or malformed required configuration stops evaluation safely. Disabled approval returns level `none` and does not write a policy-match snapshot.

## Snapshots

Every positive evaluation appends `approval.policy.matched` with the evaluated entity, trusted actor, selected level, reason, permission, and all matched policy codes.

## API Reference

| Method and path | Permission | Purpose |
|---|---|---|
| `POST /api/v1/approval-policies/evaluate` | `workflow.bpp.policy_read` | Evaluate configured approval policy |
| `GET /api/v1/approval-policies/bpp-purchasing/defaults` | `workflow.bpp.policy_read` | Read the code-owned starter catalog |
| `POST /api/v1/approval-policies/bpp-purchasing/seed-defaults` | `workflow.bpp.policy_manage` | Upsert permissions and policy configuration |

## Validation

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```
