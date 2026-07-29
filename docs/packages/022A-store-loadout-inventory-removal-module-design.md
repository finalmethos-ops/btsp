# Package 022A — Store Loadout & Inventory Removal Module Design

## Purpose

Store Loadout manages the post-event breakdown, store assignment, pickup validation, damage notation, departure scheduling, and final sign-off for sold/demo vendor hall inventory leaving the venue.

This package completes the physical event lifecycle:

`Vendor Hall Setup → Live Purchase / Assignment → Store Loadout → Signed Packing List → Venue Release`

## Core users

- Admin / Purchasing
  - configure store loadout for an event
  - assign full booths, partial booths, or selected inventory items to stores
  - split item quantities across stores
  - maintain pickup priority, zones, and departure schedule
  - monitor live loadout progress and exceptions
  - export packing lists and exception reports
- Store staff
  - mobile-only event-scoped experience
  - view only assigned store/entity inventory
  - check items as found
  - notate damage, missing items, and quantity mismatches
  - upload photos in later implementation slices
  - sign final packing list

## Domain boundaries

Store Loadout does not replace Vendor Hall inventory. It consumes validated Vendor Hall inventory and creates assignment records that point back to source booth/items.

- Vendor Hall answers: “What is physically in the booth?”
- Store Loadout answers: “Which store is removing it, when, and with what sign-off?”

## Statuses

### Store loadout status

- `not_started`
- `in_progress`
- `exceptions_present`
- `ready_for_final_review`
- `signed_complete`
- `released_from_venue`

### Loadout item status

- `assigned`
- `found`
- `damaged`
- `missing`
- `quantity_mismatch`
- `substituted`
- `removed`
- `signed_off`

## Suggested tables

- `store_loadout_events`
- `store_loadout_assignments`
- `store_loadout_items`
- `store_loadout_item_checkins`
- `store_loadout_signoffs`
- `store_loadout_audit_log`

## Security rules

Store staff access is event-scoped and assignment-scoped.

Store users may not:

- view other stores’ assignments
- view full vendor hall inventory
- change assigned quantities unless explicitly granted later
- access vendor setup, ordering, or admin modules

Admin and Purchasing users may manage all assignment and schedule records.

## Scheduling model

The first scheduling model stores admin-entered values:

- distance miles
- estimated drive minutes
- recommended departure time
- loadout priority
- loadout zone

Later packages can automate these values using a mapping/distance provider.

## Implementation package sequence

- 022A — module design
- 022B — domain foundation, assignments, progress summary
- 022C — store mobile checklist and item check-in
- 022D — signature, final packing list, and release workflow
- 022E — departure scheduling optimization
- 022F — loadout dashboard/map
- 022G — reports and final closeout exports
