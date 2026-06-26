# Implementation Package 001G — Configuration Change Snapshots & Seed Defaults

## Objective

Make configuration changes auditable and provide safe starter defaults for workflow and region behavior.

## Scope

This package adds:

- Configuration change snapshot recording
- Default configuration entries
- Configuration seed service
- Protected seed-defaults endpoint
- Tests for seeded configuration defaults
- Architecture notes for configuration defaults

## API Surface

- `POST /api/v1/configuration/seed-defaults`

## Seeded Defaults

- BPP ordering enabled
- Independent ordering enabled
- Multi-store region lock enabled
- Snapshot recording enabled

## Architecture Rules Supported

- Configuration over code
- Snapshots are immutable
- BPP and Independent workflows remain separate
- Region-locked ordering starts enabled by default

## Validation Targets

```bash
cd backend
pytest
ruff check app tests
```

## Notes

This package prepares BTSP for configurable ordering behavior. Future packages can add administrative UI, approvals, and environment-specific default bundles.
