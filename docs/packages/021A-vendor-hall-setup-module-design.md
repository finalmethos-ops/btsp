# Package 021A — Vendor Hall Setup Module Design

## Outcome

Module 021 adds a Vendor Hall Setup capability for event-based vendor fairs, leadership meetings, and trade-show style buying events. The module manages booth inventory before the event, supports vendor self-submission, enables staff physical check-in and exception capture during setup, and gives admins a live vendor hall operational view.

This package is the design baseline for implementation. It defines the domain model, statuses, workflows, permissions, API surface, UI modules, reporting/export needs, and implementation sequence.

## Core purpose

Vendor Hall Setup answers four operational questions:

- What inventory does each vendor expect to show in their booth?
- Which booth items are available for sale to Buddy’s?
- Has staff physically verified what is present, missing, damaged, or different?
- What is the live readiness state of the vendor hall before and during the event?

The module should pair naturally with Live Event Ordering, Event Vendor Booths, Staff Tasks, Event Attendance, and event-specific branding.

## Relationship to existing event platform

Vendor Hall Setup should build on the current event model instead of creating an isolated event system.

- `managed_events` remains the parent event.
- `managed_sub_events` can enable the `vendor-hall-setup` module control.
- Existing vendor event memberships identify which vendor users can manage booth inventory.
- Existing event vendor booth profiles provide booth identity, booth number, and vendor linkage.
- Event theme colors and branding image should drive all attendee/vendor/staff Vendor Hall screens.

Recommended module code:

```text
vendor-hall-setup
```

Recommended display name:

```text
Vendor hall setup
```

## Primary actors

### Vendor attendee

Vendor users can work only within events and booths assigned to their vendor membership.

Capabilities:

- Open assigned booth workspace.
- Import booth inventory listing.
- Add booth inventory manually.
- Edit draft inventory.
- Mark items available for sale to Buddy’s.
- Add price, quantity, model number, serial number, condition, and notes.
- Upload item photos or spec sheets.
- Submit booth inventory for review.
- View staff check-in status and exceptions once staff validation begins.

### Staff attendee

Staff users can work only within the events and booths assigned by their event role/scope.

Capabilities:

- Open assigned vendor booth.
- View expected submitted inventory.
- Search or scan inventory items.
- Check items in.
- Mark damages.
- Add photos.
- Mark item as not in booth.
- Add exception notes.
- Complete booth inventory validation.
- Mark booth as fully checked in.

### Admin

Admins can oversee the full vendor hall for the event.

Capabilities:

- View live show floor map.
- View all booth statuses.
- View completion percentage.
- View exception lists.
- View vendors not submitted.
- View damaged/missing items.
- View items available for sale.
- View staff check-in progress.
- Export final vendor hall data.

## Domain model

The following tables are recommended for implementation.

### `vendor_hall_events`

Represents module configuration for a managed event.

Recommended fields:

- `id`
- `event_id`
- `sub_event_id` nullable, when setup is tied to one show-floor sub-event
- `status`
- `opens_at`
- `vendor_submission_deadline`
- `staff_checkin_opens_at`
- `staff_checkin_deadline`
- `allow_vendor_edits_after_submission`
- `require_staff_checkin`
- `created_by`
- `created_at`
- `updated_at`

### `vendor_hall_booths`

Represents an operational booth in the vendor hall.

Recommended fields:

- `id`
- `vendor_hall_event_id`
- `event_vendor_booth_id`
- `event_id`
- `vendor_code`
- `booth_number`
- `booth_name`
- `floor_map_zone`
- `map_x`
- `map_y`
- `map_width`
- `map_height`
- `status`
- `submitted_at`
- `submitted_by`
- `checkin_started_at`
- `checkin_completed_at`
- `checked_in_by`
- `admin_reviewed_at`
- `admin_reviewed_by`
- `closed_at`
- `closed_by`
- `created_at`
- `updated_at`

Uniqueness:

- one active booth per `event_id` + `vendor_code` + `booth_number`

### `vendor_hall_vendors`

Optional projection table if the system needs a denormalized vendor-hall vendor roster.

Recommended fields:

- `id`
- `vendor_hall_event_id`
- `vendor_code`
- `vendor_name`
- `primary_contact_name`
- `primary_contact_email`
- `status`
- `created_at`
- `updated_at`

This can be deferred if existing catalog vendor and event membership records are sufficient.

### `vendor_hall_inventory_items`

Represents expected or actual booth inventory items.

Recommended fields:

- `id`
- `vendor_hall_booth_id`
- `event_id`
- `vendor_code`
- `source`
- `source_import_id`
- `model_number`
- `serial_number`
- `item_name`
- `description`
- `quantity_expected`
- `quantity_checked_in`
- `unit_price`
- `currency`
- `condition`
- `status`
- `available_for_sale`
- `sell_to_buddys_price`
- `notes`
- `vendor_notes`
- `staff_notes`
- `created_by`
- `created_at`
- `updated_at`

Recommended indexes:

- `vendor_hall_booth_id`
- `event_id`
- `vendor_code`
- `model_number`
- `serial_number`
- `status`
- `available_for_sale`

### `vendor_hall_inventory_imports`

Tracks vendor inventory uploads.

Recommended fields:

- `id`
- `vendor_hall_booth_id`
- `filename`
- `content_type`
- `row_count`
- `accepted_count`
- `rejected_count`
- `status`
- `error_summary`
- `uploaded_by`
- `uploaded_at`
- `completed_at`

Import should support CSV/XLSX first. Images/spec sheets should be separate item attachments.

### `vendor_hall_item_attachments`

Stores photos and spec sheets for inventory items.

Recommended fields:

- `id`
- `inventory_item_id`
- `attachment_type`
- `filename`
- `content_type`
- `content`
- `uploaded_by`
- `uploaded_at`

Bounds:

- enforce accepted content types
- enforce file size limit
- limit attachment count per item

### `vendor_hall_item_checkins`

Immutable or append-oriented check-in activity for each item.

Recommended fields:

- `id`
- `inventory_item_id`
- `vendor_hall_booth_id`
- `status`
- `quantity_checked`
- `condition`
- `damage_notes`
- `exception_notes`
- `checked_by`
- `checked_at`

### `vendor_hall_booth_checkins`

Represents booth-level staff check-in sessions.

Recommended fields:

- `id`
- `vendor_hall_booth_id`
- `status`
- `started_by`
- `started_at`
- `completed_by`
- `completed_at`
- `completion_percentage`
- `items_expected`
- `items_checked`
- `exceptions_count`
- `notes`

### `vendor_hall_exceptions`

Represents current and historical exceptions.

Recommended fields:

- `id`
- `vendor_hall_booth_id`
- `inventory_item_id` nullable
- `exception_type`
- `severity`
- `status`
- `description`
- `created_by`
- `created_at`
- `resolved_by`
- `resolved_at`
- `resolution_notes`

Exception types:

- `damaged`
- `missing`
- `quantity_mismatch`
- `unexpected_item`
- `documentation_missing`
- `price_issue`
- `other`

### `vendor_hall_floor_maps`

Stores a lightweight show floor layout.

Recommended fields:

- `id`
- `vendor_hall_event_id`
- `name`
- `image_filename`
- `image_content_type`
- `image_content`
- `layout_json`
- `uploaded_by`
- `uploaded_at`
- `is_active`

`layout_json` can hold booth coordinates, labels, dimensions, locked zones, and display metadata.

### `vendor_hall_audit_log`

Captures vendor hall operational actions.

Recommended fields:

- `id`
- `event_id`
- `vendor_hall_event_id`
- `vendor_hall_booth_id` nullable
- `inventory_item_id` nullable
- `action`
- `actor`
- `payload`
- `created_at`

This can coexist with BTSP’s platform audit/snapshot model. Critical state transitions should also emit platform audit evidence if available.

## Status model

### Booth status

Recommended enum values:

- `draft`
- `inventory_submitted`
- `checkin_in_progress`
- `fully_checked_in`
- `exceptions_present`
- `admin_reviewed`
- `closed`

Map status to live floor colors:

| Status | Color | Meaning |
| --- | --- | --- |
| `draft` | Gray | Not submitted |
| `inventory_submitted` | Blue | Vendor inventory submitted |
| `checkin_in_progress` | Yellow | Staff check-in in progress |
| `fully_checked_in` | Green | Fully checked in |
| `exceptions_present` | Red | Exceptions exist |
| `closed` | Black/locked | Booth closed or unavailable |
| `admin_reviewed` | Green with reviewed marker | Admin reviewed after check-in |

### Item status

Recommended enum values:

- `expected`
- `checked_in`
- `damaged`
- `not_in_booth`
- `quantity_mismatch`
- `available_for_sale`
- `purchased`
- `removed`

Important note: `available_for_sale` can be a boolean capability as well as a status. The recommended model is:

- `status` represents operational physical-validation state.
- `available_for_sale` represents purchase availability.

This avoids conflicts such as an item being both `damaged` and `available_for_sale`.

### Import status

Recommended enum values:

- `uploaded`
- `processing`
- `completed`
- `completed_with_errors`
- `failed`

### Exception status

Recommended enum values:

- `open`
- `resolved`
- `waived`

## Workflow design

### Vendor inventory submission

1. Vendor opens assigned event booth.
2. Vendor imports CSV/XLSX inventory or adds items manually.
3. Vendor reviews draft inventory.
4. Vendor marks which items are available for sale to Buddy’s.
5. Vendor uploads item photos/spec sheets where needed.
6. Vendor submits inventory.
7. Booth status changes from `draft` to `inventory_submitted`.
8. Staff/admin can now validate the booth.

Rules:

- Vendor can edit draft inventory before submission.
- Post-submission edits should either be locked or create a revision depending on event configuration.
- Vendor may only access booths tied to their vendor membership.

### Staff booth check-in

1. Staff opens assigned booth.
2. Staff starts booth check-in.
3. Booth status changes to `checkin_in_progress`.
4. Staff checks expected items in by search/scan/manual selection.
5. Staff records condition, damages, missing items, and quantity mismatch.
6. Staff adds photos/notes for exceptions.
7. Staff completes booth validation.
8. If no exceptions remain, booth status changes to `fully_checked_in`.
9. If exceptions exist, booth status changes to `exceptions_present`.

Rules:

- Staff check-in actions should be actor-attributed.
- Exceptions must remain visible after booth completion.
- Completing a booth should require every expected item to be resolved to a final state.

### Admin oversight

1. Admin opens Vendor Hall dashboard.
2. Admin views live map and summary metrics.
3. Admin filters by booth status, exception type, vendor, sale availability, or staff assignee.
4. Admin opens booth detail from map or list.
5. Admin reviews inventory, exceptions, and staff notes.
6. Admin marks booth reviewed or sends back for follow-up.
7. Admin exports final reports.

## Permissions

Recommended permission codes:

- `vendor_hall.read`
- `vendor_hall.manage`
- `vendor_hall.vendor.manage`
- `vendor_hall.staff.checkin`
- `vendor_hall.export`
- `vendor_hall.map.manage`

Suggested access:

| Permission | Admin | Staff | Vendor |
| --- | --- | --- | --- |
| `vendor_hall.read` | yes | yes | scoped |
| `vendor_hall.manage` | yes | no | no |
| `vendor_hall.vendor.manage` | yes | no | scoped |
| `vendor_hall.staff.checkin` | yes | yes | no |
| `vendor_hall.export` | yes | optional | no |
| `vendor_hall.map.manage` | yes | no | no |

Vendor access must always be scoped to event membership and vendor code.

Staff access should be scoped by event membership, task scope, or explicit booth assignment.

## API surface

Recommended routes:

### Vendor-facing

- `GET /api/v1/vendor-hall/mine`
- `GET /api/v1/vendor-hall/booths/{booth_id}`
- `POST /api/v1/vendor-hall/booths/{booth_id}/inventory-imports`
- `POST /api/v1/vendor-hall/booths/{booth_id}/inventory-items`
- `PUT /api/v1/vendor-hall/inventory-items/{item_id}`
- `POST /api/v1/vendor-hall/inventory-items/{item_id}/attachments`
- `POST /api/v1/vendor-hall/booths/{booth_id}/submit`

### Staff-facing

- `GET /api/v1/vendor-hall/staff/booths`
- `GET /api/v1/vendor-hall/staff/booths/{booth_id}`
- `POST /api/v1/vendor-hall/staff/booths/{booth_id}/start-checkin`
- `POST /api/v1/vendor-hall/staff/items/{item_id}/checkin`
- `POST /api/v1/vendor-hall/staff/items/{item_id}/exception`
- `POST /api/v1/vendor-hall/staff/booths/{booth_id}/complete-checkin`

### Admin-facing

- `GET /api/v1/vendor-hall/events/{event_id}/summary`
- `GET /api/v1/vendor-hall/events/{event_id}/booths`
- `GET /api/v1/vendor-hall/events/{event_id}/exceptions`
- `POST /api/v1/vendor-hall/events/{event_id}/floor-map`
- `PUT /api/v1/vendor-hall/events/{event_id}/floor-map/layout`
- `POST /api/v1/vendor-hall/booths/{booth_id}/admin-review`

### Exports

- `GET /api/v1/vendor-hall/events/{event_id}/exports/full-inventory`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/available-for-purchase`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/damaged-items`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/missing-items`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/vendor-summary`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/booth-completion`
- `GET /api/v1/vendor-hall/events/{event_id}/exports/staff-activity`

## UI modules

### Vendor attendee portal

Location:

- attendee dashboard vendor booth card
- My Events / vendor scoped event workspace

Screens:

- Booth inventory dashboard
- Import inventory
- Manual item editor
- Item detail with attachments
- Submit inventory
- Submission status and staff exceptions

### Staff check-in tool

Location:

- staff attendee landing page
- My Events sub-event tool when `vendor-hall-setup` is enabled

Screens:

- Assigned booths list
- Booth check-in workspace
- Item search/scan
- Item validation modal
- Exception capture
- Complete booth check-in

### Live vendor hall map

Location:

- My Events admin tools
- staff oversight view

Screens:

- Floor map with booth indicators
- Booth details drawer
- Exception panel
- Vendor sale availability panel

### Admin oversight

Location:

- My Events admin workspace
- future Analytics/Admin reporting

Screens:

- Summary metrics
- Booth completion list
- Exception list
- Vendor not submitted list
- Damaged/missing item reports
- Export panel

## Reports and exports

Required export outputs:

- Full booth inventory
- Items available for purchase
- Damaged item report
- Missing item report
- Vendor-by-vendor summary
- Booth completion report
- Staff check-in activity log

Export requirements:

- CSV first, XLSX later if needed.
- Escape spreadsheet formulas.
- Include event ID, event name, vendor code, booth number, item status, and timestamps.
- Enforce `vendor_hall.export`.
- Bound row counts and memory usage.

## Import rules

Initial inventory import should support CSV/XLSX with these normalized columns:

- `model_number`
- `serial_number`
- `item_name`
- `description`
- `quantity`
- `unit_price`
- `condition`
- `available_for_sale`
- `sell_to_buddys_price`
- `notes`

Validation:

- `item_name` required.
- quantity must be positive.
- price fields must be non-negative currency values.
- serial number optional but searchable.
- condition must map to allowed condition values.

Recommended condition values:

- `new`
- `floor_model`
- `open_box`
- `used`
- `damaged`
- `unknown`

## Security and data integrity

- All routes require authentication.
- Vendor routes must verify active event membership and matching vendor code.
- Staff routes must verify active event staff/admin membership.
- Admin routes must require `vendor_hall.manage`.
- Export routes must require `vendor_hall.export`.
- File uploads must enforce size and content-type bounds.
- Vendor imports must not overwrite submitted inventory without an explicit revision rule.
- Staff check-in completion must be transactional.
- Audit entries must be actor-attributed.

## Implementation sequence

### 021B — Vendor Hall Domain Foundation

- Add permissions.
- Add module code `vendor-hall-setup`.
- Add vendor hall event, booth, item, import, attachment, check-in, exception, floor-map, and audit models.
- Add migration.
- Add schemas and service layer.
- Seed baseline permissions.

### 021C — Vendor Booth Inventory Portal

- Vendor-scoped APIs.
- Manual item editor.
- Inventory import.
- Attachment upload.
- Submit inventory workflow.
- Vendor landing widget.

### 021D — Staff Check-In Tool

- Staff-scoped booth list.
- Item search/check-in.
- Damage/missing/quantity mismatch workflows.
- Exception capture.
- Complete booth validation.

### 021E — Live Vendor Hall Map

- Floor map upload/layout.
- Booth coordinate editor.
- Live booth status indicators.
- Booth detail drawer.

### 021F — Admin Oversight and Exports

- Summary dashboard.
- Exception list.
- Vendor not submitted list.
- Damaged/missing reports.
- Export endpoints.
- Activity log view.

### 021G — Production Validation

- Authorization boundary tests.
- Vendor scoping tests.
- Staff scoping tests.
- Import validation tests.
- Export formula escaping tests.
- Docker migration validation.
- Local smoke tests.

## Acceptance criteria for 021A

- Domain model is defined.
- Status model is defined.
- Vendor, staff, and admin workflows are defined.
- API surface is defined.
- UI modules are defined.
- Reports and exports are defined.
- Security boundaries are defined.
- Implementation package breakdown is defined.

## PDF floor-plan import and digitization

The implemented floor-map setup uses an uploaded PDF as its source rather than requiring administrators to draw a venue map manually.

- Admins upload a PDF after vendor booth profiles have been synced into Vendor Hall.
- BTSP stores the original PDF and displays its first page behind the live interactive booth layer.
- Text and coordinates are extracted from every PDF page; the page with the strongest unique booth matches becomes the interactive source page.
- Extracted labels are matched in priority order against booth number, booth name, and vendor code.
- Matched booths receive normalized X/Y coordinates and default interactive dimensions.
- The import records detected and unmatched booth counts, page count, scan method, and review status.
- Re-importing a revised PDF refreshes automatically detected positions.
- Admins can review any match, select a booth, and click the correct PDF location to position or reposition it without drawing or entering coordinates.
- Text-based/vector PDFs support automatic detection. Image-only scanned PDFs are retained and displayed, but require OCR support before labels can be positioned automatically.
