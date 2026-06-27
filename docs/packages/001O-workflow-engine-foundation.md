# Implementation Package 001O — Workflow Engine Foundation

## Objective

Introduce a reusable state engine for BTSP business processes.

## Scope

This package adds:

- Workflow definition model
- Workflow instance model
- Flow API schemas
- Engine service
- Definition save behavior
- Instance start behavior
- Action execution behavior
- Permission-aware validation
- Snapshot recording
- API routes
- Router registration
- Alembic migration
- Rule tests
- Architecture notes

## API Surface

- `POST /api/v1/workflow-engine/definitions`
- `POST /api/v1/workflow-engine/instances`
- `POST /api/v1/workflow-engine/instances/{instance_id}/actions`

## Validation Targets

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```

## Notes

This package creates the reusable engine foundation. Specific BPP and Independent process definitions and screens remain future packages.
