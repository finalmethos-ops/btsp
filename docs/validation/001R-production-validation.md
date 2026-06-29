# 001R Core Purchasing Domain Model Validation

## Validation metadata

- Validation date: 2026-06-28
- Host: Windows 11, WSL 2, Docker Desktop, PowerShell
- Docker Engine: 29.5.3
- Docker Compose: 5.1.4
- Backend runtime: Linux, Python 3.12
- Frontend runtime: Linux, Node 20
- Git commit SHA: `81cc33d80ad44d48b1814e9b9718508074756268`
- Worktree: dirty with the uncommitted 001P–001R increment

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| Repository integrity | Pass | `git diff --check` found no whitespace errors |
| Compose configuration | Pass | Production merge validated; persistent attachment volume present |
| Docker build/start | Pass | Backend and frontend images built; all services started |
| Database migration | Pass | `0011_purchase_attachments (head)` |
| Backend tests | Pass | 87 tests passed in 5.98 seconds |
| Backend lint | Pass | Ruff clean for `app` and `tests` |
| Frontend tests | Pass | 7 tests across 4 files |
| Frontend build | Pass | Next.js 16.2.9 production build and TypeScript passed |
| Health/readiness | Pass | API returned `ok` and `ready` |
| Nginx routes | Pass | BPP and Independent purchasing pages returned HTTP 200 |

## Live purchasing scenario

The following scenario passed against PostgreSQL and the production Compose services:

1. Seed the BPP workflow and purchasing configuration defaults.
2. Upload a canonical Excel workbook to the internal catalog.
3. Create a BPP Purchase Request for an active official store.
4. Add a catalog line with quantity 2, unit price 125, freight 10, and tax 5.
5. Confirm the calculated extended amount is 265.
6. Upload a signature-validated PDF quote and persist its checksum metadata.
7. Confirm backend readiness is true.
8. Submit the request and execute all eleven BPP happy-path transitions.
9. Confirm workflow state/status are `completed`/`complete`.
10. Confirm Purchase Request status is `completed`.
11. Confirm 15 immutable request/workflow/attachment snapshots.

## Performance evidence

A live canonical workbook containing one vendor and 500 products imported and committed in 0.522
seconds on the validation workstation. This is a baseline smoke measurement, not a production sizing
guarantee; site-specific load and concurrency testing remains an operational responsibility.

## Security and negative-path coverage

Automated coverage verifies:

- Workflow submit and transition permissions.
- Region-locked Independent ordering.
- Invalid and completed workflow transitions.
- Request ownership checks with system-administrator override.
- Inactive/unavailable store, vendor, and product rejection.
- Minimum/maximum quantities and configured restrictions.
- Stale draft revision rejection.
- Invalid business configuration fails closed.
- Attachment size/type/signature/path controls and draft-only deletion.
- Required attachment categories block readiness when absent.
- Submitted drafts cannot be mutated through draft operations.

## Known limitations

- Attachment signature checks are not malware scanning; production storage must provide scanning
  until a dedicated scanner is added.
- File-volume and PostgreSQL backups must be captured at the same maintenance boundary.
- The frontend presents the current workflow state rather than a full historical event timeline;
  immutable history is available through snapshots.
- External vendor clients and live vendor APIs are intentionally outside 001R scope.

## Go/no-go decision

**GO for Epic 001S — Purchase Order Engine.**

All 001R Definition of Done commands passed, the live aggregate completed its workflow, domain status
projection remained synchronized, snapshots were present, and no blocking defect was found.
