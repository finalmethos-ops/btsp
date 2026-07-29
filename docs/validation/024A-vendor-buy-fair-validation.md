# Package 024A Validation

- `vendor-buy-fair` is available as a selectable sub-event control.
- Vendor event landing pages route the module to the branded buy-fair workspace.
- Booth inventory model numbers are matched to active vendor catalog models and sorted first.
- Full active vendor catalog models remain available.
- Created requests use `Event Name-Store-Vendor-XXX` numbering.
- Bulk store selection increments the vendor sequence for every generated request.
- Canceled drafts do not expose or reuse their sequence number.
- Requests are standard `VENDOR_ORDER` records with event context.
- Submitted requests enter the standard Purchasing review queue.
- Admin reporting aggregates orders, units, volume, drafts, vendors, and submissions across the event.
- Admin reporting includes vendor rollups, order-level status detail, and CSV export.
- Standard Purchasing review labels buy-fair orders with their event and sub-event source.
- Submitted orders contribute to settlement and executive closeout totals without double-counting.
- Drafts block closeout and canceled drafts remain only as historical backup evidence.
- Complete Excel backups group Buy Fair lines by entity, vendor, region, and store.
- Closed settlements prevent every Buy Fair mutation.
- Service coverage verifies model priority, numbering, event context, Purchasing handoff, reporting totals, and non-reused canceled sequences.

Validation completed with:

- Backend Ruff checks
- Full backend suite: 257 passed
- Frontend ESLint
- Frontend TypeScript check
- Frontend production build
- API OpenAPI route registration check
- Backend and event page HTTP smoke checks
- Single migration head: `0075_event_backup_artifacts`
