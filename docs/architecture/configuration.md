# Configuration Foundation

BTSP uses database-backed configuration for business rules that vary by scope.

## Purpose

Configuration entries keep business behavior adjustable without requiring code changes for every store, region, workflow, or buying group variation.

## Scope Model

Each entry has:

- `scope_type`
- `scope_key`
- `key`
- `value`
- `is_active`
- `updated_by`

Examples:

- workflow / BPP / ordering.enabled
- workflow / INDEPENDENT / ordering.enabled
- region / SOUTHEAST / max.multi_store.count
- store / 1001 / ordering.enabled

## Rules

- Configuration should be preferred over code for variable business behavior.
- Configuration changes must be auditable.
- Workflow-specific settings must not merge BPP and Independent behavior.
- Region and store scoped settings must respect the Official Store Database.
