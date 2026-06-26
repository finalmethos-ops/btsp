# Implementation Package 001J — Permission Enforcement Foundation

## Objective

Move protected BTSP APIs from authentication-only access to explicit role and permission-based enforcement.

## Scope

This package adds:

- Reusable permission helpers
- `require_permission()` route dependency
- Permission enforcement on user administration routes
- Permission enforcement on configuration routes
- Permission enforcement on store authority routes
- Permission enforcement on snapshot routes
- Permission helper tests
- Permission enforcement architecture documentation

## Applied Permissions

- `system.admin`
- `configuration.manage`
- `stores.manage`
- `snapshots.read`

## Architecture Rules Supported

- Single login with role-based routing
- Configuration over code
- BPP and Independent workflow permissions remain separate
- Every protected business action must declare required permission

## Validation Targets

```bash
cd backend
pytest
ruff check app tests
```

## Notes

This package establishes route-level permission enforcement. Future packages should add workflow-specific permissions as business actions are introduced.
