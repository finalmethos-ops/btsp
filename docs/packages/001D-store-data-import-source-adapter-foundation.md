# Implementation Package 001D — Store Data Import & Source Adapter Foundation

## Objective

Create a controlled import path for store authority data while keeping source-specific integration details outside core BTSP store logic.

## Scope

This package adds:

- Store batch request, row, result, and error schemas
- Store batch validation service
- Protected store batch API endpoint
- Store source adapter protocol
- In-memory source adapter for tests and future admin tooling
- Tests for store batch validation
- Source adapter architecture documentation

## API Surface

- `POST /api/v1/stores/batch`

## Architecture Rules Supported

- Store data remains the source of truth for identity, region, district, and eligibility
- Configuration over code
- Region-locked ordering readiness
- BPP and Independent workflows remain separate from shared store authority data

## Validation Targets

```bash
cd backend
pytest
ruff check app tests
```

## Notes

This package does not implement a specific upstream feed. CSV, API, scheduled job, and database source adapters remain future packages.
