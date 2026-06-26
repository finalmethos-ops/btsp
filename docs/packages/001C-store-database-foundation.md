# Implementation Package 001C — Store Database Foundation

## Objective

Establish the store database foundation for store identity, region, district, ordering eligibility, and future multi-store ordering controls.

## Scope

This package adds:

- Expanded store model for operational fields
- Store upsert, lookup, list, and region-scope service logic
- Protected store API routes
- Region scope validation endpoint
- Additive Alembic migrations for store operational and audit fields
- Store response and upsert schemas
- Region scope request and result schemas
- Region scope service test

## Architecture Rules Supported

- Store data is treated as the system store authority
- Region-locked multi-store ordering
- Configuration over code
- Audit-ready store tracking
- BPP and Independent workflows can share store truth without merging workflows

## API Surface

- `GET /api/v1/stores`
- `GET /api/v1/stores/{store_number}`
- `POST /api/v1/stores/upsert`
- `POST /api/v1/stores/scope-check`

## Validation Targets

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```

## Notes

This package creates the store authority foundation. External feed ingestion, reconciliation, administrative UI, and adapter work remain future packages.
