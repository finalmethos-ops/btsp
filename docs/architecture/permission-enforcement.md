# Permission Enforcement

BTSP uses explicit permission codes for protected actions.

## Pattern

Routes that need authorization use `require_permission("permission.code")`.

## Current Permissions Applied

- `system.admin` for user administration and manual snapshot creation
- `configuration.manage` for configuration read/write and seed defaults
- `stores.manage` for store authority management and region scope checks
- `snapshots.read` for snapshot history reads

## Rules

- Authentication alone is not sufficient for protected administration endpoints.
- Permission checks should be applied at route boundaries.
- BPP and Independent workflow permissions must remain separate.
- New packages must define permissions before adding protected business actions.
