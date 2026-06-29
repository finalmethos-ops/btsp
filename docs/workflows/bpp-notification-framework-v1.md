# BPP Notification Framework — Version 1

## Purpose

The notification framework converts workflow events into persisted, rendered notification events without hard-coding recipients, templates, or delivery channels.

Configuration namespace: `workflow.bpp_purchasing.notifications`

## Notification Event Catalog

- `workflow.started`
- `workflow.advanced`
- `approval.policy.matched`
- `bpp.submitted`
- `bpp.revision_requested`
- `bpp.rejected`
- `bpp.approved`
- `bpp.po_created`
- `bpp.vendor_submitted`
- `bpp.vendor_confirmed`
- `bpp.shipment_scheduled`
- `bpp.receiving_ready`
- `bpp.completed`

Templates can be created for any of these events. Version 1 seeds the eight BPP templates listed below.

## Template Model

Each template contains:

- Unique `template_code`
- `workflow_code` and `event_type`
- Delivery `channel`
- `subject_template` and `body_template`
- `recipient_strategy` and JSON `recipient_config`
- Active status and creation/update timestamps

Subject and body templates use Python-style named placeholders such as `{entity_id}`, `{actor}`, and context fields supplied during emission. Missing placeholders produce a failed notification event rather than an unrendered message.

## Recipient Strategy Catalog

| Strategy | Resolution |
|---|---|
| `actor` | Event actor |
| `workflow_role` | Active users assigned configured role codes |
| `permission_holders` | Active users holding configured permissions |
| `region_admins` | Active regional users assigned configured admin roles |
| `store_users` | Active users assigned to the event's store |
| `static_recipients` | Deduplicated configured recipient list |

`region_admins` reads `region_code` and `store_users` reads `store_number` from event context.

## Channel Behavior

| Channel | Version 1 behavior |
|---|---|
| `in_app` | Persisted with status `queued` |
| `email` | Delivery adapter stub; persisted with status `queued` |
| `webhook` | Delivery adapter stub; `skipped` unless webhook configuration is enabled |

All channels honor `notification.enabled` and `notification.channels`. Delivery workers can later mark queued events `sent` or `failed` through the service contract.

## Configuration Reference

All entries use scope type `workflow` and scope key `BPP_PURCHASING`.

| Key | Default value |
|---|---|
| `notification.enabled` | `{"enabled": true}` |
| `notification.channels` | `{"channels": ["in_app", "email"]}` |
| `notification.default_channel` | `{"channel": "in_app"}` |
| `notification.digest_enabled` | `{"enabled": false}` |
| `notification.webhook_enabled` | `{"enabled": false}` |

## Seed Template Catalog

| Template | Event | Recipient strategy |
|---|---|---|
| `BPP_SUBMITTED_IN_APP` | `bpp.submitted` | `workflow_role` |
| `BPP_REVISION_REQUESTED_IN_APP` | `bpp.revision_requested` | `actor` |
| `BPP_REJECTED_IN_APP` | `bpp.rejected` | `actor` |
| `BPP_APPROVED_IN_APP` | `bpp.approved` | `actor` |
| `BPP_PO_CREATED_IN_APP` | `bpp.po_created` | `workflow_role` |
| `BPP_VENDOR_SUBMITTED_IN_APP` | `bpp.vendor_submitted` | `workflow_role` |
| `BPP_VENDOR_CONFIRMED_IN_APP` | `bpp.vendor_confirmed` | `workflow_role` |
| `BPP_COMPLETED_IN_APP` | `bpp.completed` | `actor` |

All starter templates are active and use channel `in_app`.

## API Reference

| Method and path | Permission |
|---|---|
| `GET /api/v1/notifications/templates` | `notifications.read` |
| `POST /api/v1/notifications/templates` | `notifications.manage` |
| `PATCH /api/v1/notifications/templates/{template_code}` | `notifications.manage` |
| `GET /api/v1/notifications/events` | `notifications.read` |
| `POST /api/v1/notifications/emit` | `notifications.send` |
| `POST /api/v1/notifications/seeds/bpp-purchasing` | `workflow.bpp.notifications.manage` |

The emit endpoint replaces the submitted actor with the authenticated user's email.

## Snapshot Behavior

Every persisted emission writes `notification.emitted` with workflow, source event, template, channel, strategy, and status. Rendering or resolution failures write `notification.failed` with the same entity and trusted actor.

## Validation

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```
