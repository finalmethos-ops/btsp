# Package 024A — Vendor Buy Fair Module Design

## Purpose

Vendor Buy Fair is the fourth event sub-event capability. It provides an event-branded version of the normal vendor ordering workspace while retaining BTSP's standard purchasing lifecycle and controls.

## Module control

- Code: `vendor-buy-fair`
- Label: Vendor buy fair ordering
- Assigned vendors open it from their event landing page.
- Event admins enable it from the selected sub-event's Available Controls list.

## Ordering behavior

- The model selector lists models physically present in the vendor's event booth first.
- The complete active and available vendor catalog remains selectable below the booth group.
- Vendors may build one cart and create separate store orders for one or more eligible stores.
- Drafts retain the normal vendor ordering controls for delivery date, line additions/removals, submission, and cancellation.
- Submission changes the standard `VENDOR_ORDER` purchase request to `submitted_to_purchasing`; no duplicate event-only purchasing queue is created.

## Event order identity

Event requests use:

`Event Name-Store Number-Vendor Code-XXX`

`XXX` is a three-digit, event-and-vendor sequence. The event row is locked during allocation, and canceled drafts retain their consumed number so identifiers are not reused.

## Reporting and provenance

Each standard purchase request carries event provenance in its context:

- source
- event ID and name
- sub-event ID and name
- vendor event sequence

The admin sub-event tools show event-wide vendor count, order count, drafts, submissions, units, and order volume. Vendor workspaces show the same operational measures scoped to that vendor only.

Submitted Buy Fair orders contribute to settlement, executive closeout, command-center, CSV closeout, and Excel backup totals. Drafts create a settlement blocker; canceled drafts remain historical backup evidence but do not inflate settlement totals.

## Security

- Access requires an active vendor membership for the event.
- The membership must have access to the selected sub-event.
- Every request mutation verifies event, sub-event, and vendor ownership.
- Vendor users cannot see another vendor's models, orders, or totals.
- Event-wide totals require `events.manage`.
- All Buy Fair mutations are locked after event settlement closes.
