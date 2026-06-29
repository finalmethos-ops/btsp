# 001S Purchase Order Engine Production Validation

## Validation metadata

- Validation date: 2026-06-28
- Docker Engine: 29.5.3
- Docker Compose: 5.1.4
- Database: PostgreSQL 16
- Backend runtime: Linux, Python 3.12
- Frontend runtime: Linux, Node 20

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| Compose configuration | Pass | Base and merged production configurations validated successfully |
| Image builds | Pass | Backend and frontend images rebuilt from the current worktree |
| Production commands | Pass | Merged production override launched uvicorn without reload and `next start` |
| Service health | Pass | PostgreSQL and Redis healthy; backend, frontend, and nginx running |
| Database migration | Pass | Alembic upgraded PostgreSQL through revision `0015_po_transmissions` |
| Backend lint | Pass | Ruff clean for application and tests |
| Backend tests | Pass | 116 tests passed after final release hardening |
| Dependency audits | Pass | Backend and frontend audits reported zero known vulnerabilities |
| Frontend lint | Pass | ESLint completed successfully |
| Frontend tests | Pass | Nine tests across five files passed |
| Frontend build | Pass | Next.js production build and TypeScript completed during image build |
| Readiness | Pass | `/api/v1/ready` returned `ready` after deployment and restart |
| Routed workspace | Pass | nginx returned HTTP 200 for `/purchase-orders` |

## Live PostgreSQL scenario

The repeatable validator at `backend/scripts/validate_001s_live.py` completed this scenario against
the deployed PostgreSQL database:

1. Seed BPP purchasing and PO configuration idempotently.
2. Create uniquely tagged store, user, vendor, product, and Purchase Request records.
3. Submit the request and advance it to `po_created`.
4. Generate PO `PO-2026-000004` with an atomic persisted number.
5. Generate immutable PDF, CSV, and JSON artifacts.
6. Advance the source workflow to `vendor_submission`.
7. Prepare, release, and mark an operator-controlled manual transmission delivered.
8. Confirm PO status `transmitted`, transmission status `delivered`, three immutable transmission
   events, and seven PO snapshots.

## Restart persistence

After restarting the backend container:

- PostgreSQL retained the PO, its `transmitted` status, the `delivered` transmission, and all three
  transmission events.
- The export volume retained all three artifact files.
- SHA-256 checksums remained unchanged:
  - PDF: `f0181fd0dac117b8caec5b9193c5c503ae99997bcbde9062722280cab09ef9da`
  - CSV: `213acd520a1ab4e8f9bd071eb4822945d500717c67b781c9b461b5db85cf8352`
  - JSON: `721edbcba130fa23d07c66b22667851b11815ffa00b954f812333cb2d41da6fb`

## Go/no-go decision

**GO for Epic 001T — Vendor Integration Platform.**

Epic 001S satisfies its production gate for numbering, grouping, splitting, consolidation, export
artifacts, and internal operator-controlled transmission. This decision does not claim external
vendor delivery, acknowledgement, ASN, EDI, API, shipment, or import-automation behavior; those
capabilities begin in 001T.

The final whole-project review and remediation evidence is recorded in
`001S-final-code-audit.md`.
