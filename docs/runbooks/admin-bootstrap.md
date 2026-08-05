# Admin Bootstrap Runbook

This runbook provisions the first BTSP administrator after installation.

## Prerequisites

- Database migrations have been applied.
- `BOOTSTRAP_ADMIN_TOKEN` is set in the environment.
- `BOOTSTRAP_ENABLED=true` is set only for the initial provisioning window.
- The backend service is running.

## Request

```bash
curl -X POST http://localhost:8000/api/v1/bootstrap/admin \
  -H "Content-Type: application/json" \
  -H "X-BTSP-Bootstrap-Token: change-me-before-bootstrap" \
  -d '{
    "email": "admin@example.com",
    "display_name": "BTSP Admin",
    "password": "change-this-password"
  }'
```

## Result

The endpoint creates or updates the administrator user and ensures core roles and permissions exist.

## Security Notes

- Change `BOOTSTRAP_ADMIN_TOKEN` before production use.
- Rotate the bootstrap token and set `BOOTSTRAP_ENABLED=false` after initial provisioning.
- Recreate the backend container and confirm `/api/v1/bootstrap/admin` returns HTTP 404.
- Replace the initial admin password immediately after first login.
- This endpoint is for installation bootstrap only.
