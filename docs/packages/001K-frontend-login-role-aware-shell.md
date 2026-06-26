# Implementation Package 001K — Frontend Login & Role-Aware Shell Foundation

## Objective

Create the first usable BTSP frontend flow for login, session handling, current-user loading, and role-aware workflow navigation.

## Scope

This package adds:

- Frontend API client
- Token storage helpers
- Login API call
- Current user API call
- Available workflows API call
- Auth provider and hook
- Authenticated root layout
- Global frontend styles
- Login form component
- Dashboard shell component
- Authenticated landing page
- BPP workflow placeholder page
- Independent workflow placeholder page
- Frontend workflow route test

## Frontend Flow

- Unauthenticated users see the login form.
- Authenticated users see a dashboard shell.
- Dashboard workflow cards are loaded from `/api/v1/workflows/available`.
- BPP and Independent workflow routes remain separate.

## Architecture Rules Supported

- Single login with role-based routing
- BPP and Independent workflows remain separate
- Configuration and permission-backed APIs remain backend-owned
- Frontend consumes workflow availability instead of hard-coding access decisions

## Validation Targets

```bash
cd frontend
npm install
npm run build
npm test -- --run
```

## Notes

This package creates the frontend shell foundation. Route guards, refresh tokens, SSO, administrative screens, and full workflow UIs remain future packages.
