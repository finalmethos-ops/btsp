# Package 023A Validation — Event Settlement & Post-Event Reconciliation

## Validation scope

This validation package covers the completed 023A–023F Event Settlement implementation.

## Expectations

- `event-settlement` is registered as an event module.
- Event Settlement appears as a selectable setup control for event sub-events.
- Core settlement permissions are registered:
  - `event_settlement.read`
  - `event_settlement.manage`
  - `event_settlement.export`
- Purchasing receives settlement read/manage/export permissions.
- Reconciliation receives settlement read/manage/export permissions.
- Store/franchise users do not receive settlement permissions by default.
- Settlement foundation tables exist:
  - `event_settlement_events`
  - `event_settlement_exceptions`
  - `event_settlement_audit_log`
- Settlement summary API rolls up:
  - event order totals and released order counts
  - approved units and approved spend
  - loadout assignment totals
  - signed and released loadout counts
  - open closeout exceptions
  - readiness percentage
  - approval and closure decision metadata
  - submitted Vendor Buy Fair orders without double-counting live-order purchasing releases
- Settlement summary detects generated closeout exceptions:
  - unreleased orders
  - unsigned packing lists
  - signed but unreleased stores
  - active loadout exception assignments
  - loadouts waiting on event staff final review
  - released orders not found in released loadouts
  - released loadouts without matching released orders
  - released order/loadout quantity mismatches
- Settlement summary exposes dedicated counts for order/loadout reconciliation mismatches.
- Settlement admin UI displays a focused order/loadout reconciliation panel.
- Settlement loadout closeout exports include team assignment and final review evidence.
- Settlement summary exports include approval/closure actors, timestamps, and notes.
- Settlement closeout packet export combines summary, exceptions, order closeout, loadout closeout, and audit sections into one CSV.
- Settlement reconciliation detail export lists line-level order/loadout variances with quantities and variance values.
- Event administrators can download a multi-sheet Excel backup containing both ordering channels, entity tabs, purchasing requests, and generated POs.
- Settlement closure automatically archives the exact Excel workbook with size, creator, timestamp, and SHA-256 metadata.
- Executive event members receive event-scoped, read-only closeout metrics.
- Closure completes the event/sub-events, ends presentations, closes polls and ordering, and prevents all event mutations.
- Completed events appear in the Archived My Events view with reporting/download controls only.

## Validation commands

- Full backend suite:
  - `python -m pytest -p no:cacheprovider`
- Backend lint:
  - `python -m ruff check app tests`
- Frontend lint/build:
  - `npm run lint`
  - `npm run build`

## Recorded validation result

- 257 backend tests passed.
- All backend application and test files passed Ruff.
- The frontend production build generated all 37 routes successfully.
- Alembic reports one clean head: `0075_event_backup_artifacts`.
- API readiness, `/events`, and `/event-login` returned HTTP 200.
