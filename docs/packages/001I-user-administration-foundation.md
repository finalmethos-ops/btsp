# Implementation Package 001I — User Administration Foundation

## Objective

Add protected user-management APIs so BTSP administrators can manage users after the initial bootstrap process.

## Scope

This package adds:

- User administration schemas
- User administration service
- Protected user listing endpoint
- Protected user creation endpoint
- Protected user update endpoint
- API router registration
- User administration schema tests

## API Surface

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{email}`

## Architecture Rules Supported

- Single login with role-based routing
- Role-based workflow access
- BPP and Independent workflow separation through assigned roles
- Region-aware user scope readiness

## Validation Targets

```bash
cd backend
pytest
ruff check app tests
```

## Notes

This package creates the foundation for user management. Permission enforcement middleware, password reset, lockout policy, SSO, and frontend user administration remain future packages.
