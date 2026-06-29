# BTSP Production Deployment Runbook

## Purpose

Deploy BTSP 001P repeatably to an on-premises Docker host and prove the installation is operational before accepting users.

## Prerequisites

- Supported Docker Engine and Docker Compose v2+
- Linux containers (WSL 2 on Windows hosts)
- Approved DNS, TLS, firewall, persistent storage, and backup targets
- A reviewed immutable BTSP release revision
- Production secrets supplied outside source control

## Environment Reference

| Variable | Purpose | Production guidance |
|---|---|---|
| `ENVIRONMENT` | Runtime mode | Set to `production` |
| `APP_NAME` | Display/API application name | Normally `BTSP` |
| `APP_VERSION` | Deployed release identifier | Set to approved release version |
| `SECRET_KEY` | JWT signing secret | Generate a unique high-entropy value; never use the default |
| `BOOTSTRAP_ADMIN_TOKEN` | Initial admin bootstrap secret | Generate uniquely; rotate after bootstrap |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | Use the approved short session duration |
| `CORS_ORIGINS` | Allowed browser origins | Comma-separated approved HTTPS origins; no localhost |
| `DATABASE_URL` | Backend PostgreSQL connection | Use production host, database, user, and secret |
| `ATTACHMENT_STORAGE_PATH` | Purchase attachment storage | Keep `/data/attachments` for Docker deployments |
| `ATTACHMENT_MAX_BYTES` | Maximum upload size | Default `20971520`; tune for operational policy |
| `PURCHASE_ORDER_EXPORT_PATH` | Generated PO artifact storage | Keep `/data/purchase-order-exports` for Docker deployments |
| `REDIS_URL` | Backend Redis connection | Use the production service/network name and protected instance |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-visible backend base URL | Use the externally reachable HTTPS API origin |
| `NGINX_PORT` | Host Nginx port | Match ingress/firewall design |
| `POSTGRES_DB` | Compose PostgreSQL database | Do not use shared or temporary databases |
| `POSTGRES_USER` | Compose PostgreSQL role | Use a dedicated least-privilege role |
| `POSTGRES_PASSWORD` | Compose PostgreSQL password | Replace `btsp_local_password` with a secret |

Protect `.env` with host filesystem permissions. Prefer the site's supported secret manager when available.

## Preflight Validation

1. Confirm default secrets and local database credentials are absent.
2. Confirm CORS contains only production HTTPS origins.
3. Confirm the PostgreSQL named volume maps to persistent protected storage.
4. Confirm Redis is available and not publicly exposed.
5. Confirm Nginx routing, TLS termination, and upstream ports.
6. Complete a pre-deployment backup using the database runbook.

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml config
docker compose -f docker-compose.yml -f docker-compose.production.yml build
```

Review the rendered configuration for accidental secret exposure before sharing output.

## Start and Migrate

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
docker compose -f docker-compose.yml -f docker-compose.production.yml ps
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend alembic current
```

Expected Alembic head: `0008_notification_framework`.

The production override removes source bind mounts, disables backend reload, and starts the prebuilt Next.js production server. Do not deploy the base development Compose file alone.

## Release Validation

```bash
docker compose exec backend ruff check app tests
docker compose exec backend pytest
docker compose exec frontend npm run build
docker compose exec frontend npm test -- --run
```

## Administrator Bootstrap

```bash
curl -X POST https://btsp.example/api/v1/bootstrap/admin \
  -H "Content-Type: application/json" \
  -H "X-BTSP-Bootstrap-Token: $BOOTSTRAP_ADMIN_TOKEN" \
  -d '{"email":"admin@example.com","display_name":"BTSP Admin","password":"temporary-secret"}'
```

Immediately change the administrator password through the approved administrative procedure and rotate `BOOTSTRAP_ADMIN_TOKEN` in `.env`, then recreate the backend container.

## Seed Order

Authenticate as the administrator and call these idempotent endpoints in order:

1. `POST /api/v1/configuration/seed-defaults`
2. `POST /api/v1/workflow-registry/seeds/defaults`
3. `POST /api/v1/workflow-engine/seeds/bpp-purchasing`
4. `POST /api/v1/approval-policies/bpp-purchasing/seed-defaults`
5. `POST /api/v1/notifications/seeds/bpp-purchasing`

Repeat the seed verification in a controlled installation test and confirm scoped unique keys, definition `(code, version)`, permission codes, and template codes remain unique.

## Health and Routing

```bash
curl https://btsp.example/api/v1/health
curl https://btsp.example/api/v1/ready
curl -I https://btsp.example/
```

Verify direct frontend and backend URLs only when permitted by the network design. Confirm Nginx serves the frontend and proxies `/api/` to the backend.

## Operational Log Review

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 frontend
docker compose logs --tail=200 postgres
docker compose logs --tail=200 redis
docker compose logs --tail=200 nginx
```

Look for tracebacks, restart loops, authentication failures, migration errors, database recovery messages, Redis connection failures, and upstream proxy errors. Container stdout/stderr should be forwarded to approved centralized logging in production.

## Application Verification

- Login as the administrator and call `/auth/me`.
- List the workflow registry and inspect `BPP_PURCHASING`.
- Start and advance a controlled BPP test request.
- Evaluate approval policy at known threshold boundaries.
- Emit a controlled in-app notification and review notification history.
- Review the corresponding snapshots.
- Confirm unauthorized users receive 403 responses.

## Ongoing Operations

- Monitor PostgreSQL volume capacity and backup success.
- Monitor snapshot table growth and establish retention/archive policy.
- Review queued, skipped, and failed notification events.
- Review container restarts and readiness failures.
- Rotate secrets and administrator credentials according to site policy.
- Apply future migrations only after verified backup and staging rehearsal.
