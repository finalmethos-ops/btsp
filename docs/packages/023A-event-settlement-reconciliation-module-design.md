# Package 023A — Event Settlement & Post-Event Reconciliation Module Design

## Purpose

Event Settlement converts completed event activity into an auditable closeout packet for Purchasing, Reconciliation, and leadership review.

It sits after Store Loadout:

`Vendor Hall Setup → Live Ordering → Store Assignment → Store Loadout → Signed Packing List → Event Settlement`

## Core outcomes

- prove what was ordered, assigned, removed, damaged, missing, signed, and released
- reconcile event orders against signed store loadouts
- surface settlement exceptions before finance or purchasing closeout
- produce final event closeout exports
- preserve evidence for audit and vendor/store follow-up

## Core users

- Purchasing
  - reviews approved event orders and assigned inventory
  - confirms purchasing disposition
  - exports final event settlement packet
- Reconciliation
  - resolves order/loadout/exception mismatches
  - records final settlement decisions
  - prepares finance-ready evidence
- Admin
  - monitors event closeout readiness
  - manages event-level settlement configuration
  - exports audit and closeout records
- Executives
  - event-scoped, read-only closeout visibility

## Domain boundaries

Event Settlement does not replace:

- Event Ordering, which captures demand and approved orders
- Vendor Hall, which captures booth inventory
- Store Loadout, which captures physical removal and sign-off
- Invoice Reconciliation, which handles vendor invoice/payable decisions

Event Settlement links these domains into one closeout view.

## Implemented module capabilities

The completed 023 package provides:

- event module code: `event-settlement`
- permissions:
  - `event_settlement.read`
  - `event_settlement.manage`
  - `event_settlement.export`
- Purchasing and Reconciliation roles receive settlement permissions
- admins can assign the control to event sub-events
- combined live-presentation and Vendor Buy Fair settlement totals
- order/loadout matching and generated exception detection
- approval and irreversible closure decisions with actor/timestamp evidence
- CSV closeout, reconciliation, exception, loadout, audit, and combined packet exports
- a complete multi-sheet Excel order backup with entity tabs and purchasing/PO traceability
- automatic immutable workbook archival at closure with SHA-256 verification
- admin command-center monitoring and event-scoped executive closeout insights
- closed-event mutation locks across setup, content, ordering, Vendor Hall, Loadout, and live tools

## Completed implementation sequence

- 023A — module design, registration, permissions
- 023B — settlement domain tables and summary API
- 023C — order/loadout matching and exception detection
- 023D — reconciliation decisions and closeout workflow
- 023E — settlement exports and audit packet
- 023F — admin UI and executive closeout dashboard

## Implemented tables

- `event_settlement_events`
- `event_settlement_exceptions`
- `event_settlement_audit_log`
- `event_order_backup_artifacts`

## Key statuses

### Settlement status

- `draft`
- `collecting_evidence`
- `exceptions_present`
- `ready_for_review`
- `approved`
- `closed`

### Settlement exception type

- `ordered_not_loaded`
- `loaded_not_ordered`
- `quantity_mismatch`
- `damaged_on_loadout`
- `missing_on_loadout`
- `unsigned_packing_list`
- `unreleased_store`
- `unsubmitted_buy_fair_order`

## Security expectations

- Settlement read access is limited to authorized Purchasing, Reconciliation, and Admin users.
- Executive insights require an active executive/admin membership for the specific event.
- Settlement management is limited to Purchasing/Reconciliation/Admin.
- Settlement exports require explicit export permission.
- Store users do not receive settlement permissions by default.
- Closure is irreversible and makes event operational records read-only.
