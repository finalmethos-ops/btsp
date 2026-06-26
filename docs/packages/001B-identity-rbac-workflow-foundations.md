# Implementation Package 001B — Identity, RBAC, and Workflow Foundations

## Objective

Establish the identity, access-control, and workflow-routing foundation for BTSP.

## Scope

This package adds:

- User, role, permission, user-role, and role-permission models
- Workflow code boundaries for BPP and Independent operations
- Login request and token response schemas
- Current user response schema with roles, permissions, and workflows
- Password hashing and JWT access token utilities
- Current-user dependency for protected API routes
- Authentication service logic
- Auth login and current-user routes
- Available workflows route
- Alembic migration for identity and RBAC tables
- Frontend workflow route contract
- Backend workflow separation test

## Architecture Rules Supported

- Single login with role-based routing
- BPP and Independent workflows remain separate
- Configuration over code
- Event Snapshot actor attribution readiness
- Region-aware user scope readiness

## Validation Targets

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests
```

## Notes

This package creates the foundation for real authentication. Production user provisioning, password reset, SSO integration, seed data, and admin user management remain future packages.
