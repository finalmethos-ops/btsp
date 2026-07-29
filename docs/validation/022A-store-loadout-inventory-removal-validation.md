# Package 022A Validation — Store Loadout & Inventory Removal

## Validation scope

This validation package covers the Store Loadout design and the implemented 022B–022H slices.

## Foundation expectations

- Store Loadout is registered as an event module.
- Store Loadout permissions are registered in core identity defaults.
- Admin/Purchasing can configure event-level loadout.
- Admin/Purchasing can assign Vendor Hall inventory items to stores.
- Assignment records preserve store, entity, booth, vendor, quantity, priority, zone, and schedule metadata.
- Store users can only view assignments scoped to their assigned store/entity.
- Progress summary reports not started, in progress, exceptions, signed, and released counts.
- Store mobile users can check assigned items as found, damaged, missing, substituted, or removed.
- Quantity mismatch is detected automatically.
- Store users can mark assignments ready for final review.
- Admin users can assign loadout teams with store staff and one or more event staff leads.
- Event staff leads or managers can complete final review with review notes.
- Store users can sign final packing lists only after event staff final review is complete.
- Admin users can release signed assignments from the venue.
- Admin users can export master, packing-list, damaged, missing, departure schedule, and audit CSV reports.
- Admin users can monitor live loadout progress by zone, exception queue, booth clearance, signed status, and released status.
- Store staff and event staff can upload scoped JPEG, PNG, or WebP evidence photos for assigned loadout items.
- Evidence uploads are size-limited, content-validated, event-scoped, and restricted to the assignment owner or loadout managers.
- Packing-list PDFs include route distance, drive time, recommended departure, vehicle status, team details, discrepancy notes, and evidence-photo counts.

## Security expectations

- Admin/Purchasing permissions are required for assignment management.
- Store-scoped users receive only their own loadout assignments.
- Assignment APIs validate that referenced Vendor Hall inventory belongs to the same event.
- Split quantities cannot exceed the source Vendor Hall item quantity.
- Store users cannot check in or sign another store’s assignment.
- Unassigned staff cannot complete final review for a team they do not lead.
- Store users cannot release assignments from the venue.
- Store users cannot export loadout reports.
- Store Loadout route boundary tests cover release/export permission enforcement.

## Validation evidence

- Focused Store Loadout tests cover assignment, store scoping, check-in, exceptions, team lead final review, signature gating, release, exports, and route boundaries.
- Full backend suite passed with Store Loadout included.
- Frontend lint/build passed with Store Loadout admin and mobile UI included.

## Remaining future enhancements

No remaining enhancements are outstanding for the validated loadout scope.


## Routing and departure automation

Store assignments now calculate driving distance, estimated drive time, and a
recommended departure time from the event and store addresses. The target is
arrival at 6:00 PM in the event's configured timezone. Route estimates use the
configured geocoding and routing endpoints (`GEOCODING_API_URL` and
`ROUTING_API_URL`), defaulting to OpenStreetMap Nominatim and OSRM for local
development. Admins can recalculate all active assignments after an address,
date, or provider change; team priority is refreshed automatically afterward.
