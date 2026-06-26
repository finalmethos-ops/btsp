# Implementation Package 001M — Frontend Admin User Management UI

## Objective

Connect the frontend administration shell to the user administration APIs so administrators can view, create, and update BTSP users.

## Scope

This package adds:

- Frontend user administration API client functions
- Admin user TypeScript types
- User management panel component
- User list table
- Create user form
- Edit user flow
- Active/inactive toggle
- Region and home store fields
- Role assignment controls
- Admin users route integration
- Frontend user admin payload tests

## API Usage

The UI uses:

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{email}`

## Architecture Rules Supported

- Single login with role-based routing
- User roles determine available workflows
- BPP and Independent workflows remain separate through role assignment
- Region-aware user scope fields are captured for future ordering controls

## Validation Targets

```bash
cd frontend
npm install
npm run build
npm test -- --run
```

## Notes

This package creates the first functional frontend administration screen. Role catalog management, password reset, audit trail display, and advanced filtering remain future packages.
