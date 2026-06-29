# Workflow Registry

BTSP uses a code-owned workflow registry as the canonical catalog of deployable workflow capabilities.

## Responsibilities

Each registration declares:

- Stable workflow code
- Display name
- Frontend route
- Workflow action permission

The registry currently contains separate entries for BPP and Independent ordering.

## Boundaries

- The registry identifies workflow capabilities shipped with the application.
- Database-backed workflow definitions describe versioned states and transitions for those capabilities.
- Roles assign workflow access to users.
- Configuration controls variable workflow behavior.
- The frontend consumes registry metadata from the API instead of maintaining a parallel catalog.

These responsibilities must remain separate. Registering a workflow does not create a state-machine definition, grant user access, or enable ordering configuration.

## API

- `GET /api/v1/workflows/available` returns registered workflows assigned to the authenticated user.
- `GET /api/v1/workflows/registry` returns the complete registry to users with `workflows.read`.

## Rules

- Workflow codes must be unique.
- Registration order is deterministic.
- Unknown codes are rejected by workflow-definition and instance-start operations.
- BPP and Independent routes, permissions, definitions, configuration, and audit history remain separate.
- Registry changes are delivered through reviewed application packages rather than runtime database edits.
