# 021A — Vendor Hall Setup Module Design Validation

## Validation result

Package 021A is a design package. No runtime migration, API, or UI behavior is introduced by this package.

## Reviewed scope

- Vendor attendee inventory workflow
- Staff booth check-in workflow
- Live vendor hall map workflow
- Admin oversight workflow
- Suggested database model
- Status model
- Permission model
- API surface
- UI module plan
- Export/report plan
- Implementation package sequence

## Outcome

The design is ready to proceed into `021B — Vendor Hall Domain Foundation`.

## Follow-up implementation gates

Before Module 021 is considered production-ready, later implementation packages must validate:

- vendor access scoping by event membership and vendor code
- staff check-in access scoping
- admin export authorization
- import row validation and bounded upload size
- CSV and XLSX vendor inventory imports with shared row validation
- attachment content-type and size limits
- status transition integrity
- final export formula escaping
- Docker migration upgrade from the previous head
# PDF Floor Plan Validation

- PDF uploads are restricted to valid PDF content up to 20 MB.
- The source PDF is stored and available only to authenticated Vendor Hall readers.
- Every PDF page is scanned and the page with the strongest unique booth matches is selected.
- Booth label matching uses complete alphanumeric token sequences so similar booth numbers do not create partial matches.
- Detected booths populate normalized interactive positions.
- Import metadata records detected and unmatched counts and flags the result for visual review.
- The live map layers booth status controls over the imported PDF source.
- Image-only PDFs remain usable as the source background and report zero automatic matches.
- Unmatched and incorrectly matched booths can be positioned by selecting a booth and clicking its PDF location.

# Selection Styling Validation

- Native select menus use the shared dark palette and yellow selected-option state.
- Vendor Hall and Store Loadout no longer override shared fields with white backgrounds.
- Selected cards, tabs, checkboxes, radios, options, and event controls follow the same navy/yellow contrast contract.
