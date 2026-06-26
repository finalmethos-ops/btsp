# Implementation Package 001H — Admin Bootstrap

## Objective

Create a controlled installation path for provisioning the first administrator account and core identity defaults.

## Scope

This package adds:

- Admin bootstrap schemas
- Core permission defaults
- Core role defaults
- Admin bootstrap service
- Bootstrap token setting
- Protected bootstrap API route
- API router registration
- Identity default tests
- Admin bootstrap runbook

## API Surface

- `POST /api/v1/bootstrap/admin`

## Architecture Rules Supported

- Single login with role-based routing
- BPP and Independent workflow separation
- Configuration and store APIs can be accessed by a provisioned administrator
- Production bootstrap requires non-default secrets

## Validation Targets

```bash
cd backend
pytest
ruff check app tests
```

## Notes

This package is for installation bootstrap only. Full user administration, password reset, account lockout, and SSO remain future packages.
