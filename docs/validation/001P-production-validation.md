# 001P Production Validation Report

## Validation Metadata

- Validation date: 2026-06-27
- Host: Windows 11 with WSL 2, Docker Desktop, and PowerShell
- Container backend: Linux, CPython 3.12.13
- Container frontend: Linux, Node 20
- Docker client/server: 29.5.3
- Docker Compose: 5.1.4
- Git commit SHA: `81cc33d80ad44d48b1814e9b9718508074756268`
- Worktree state: dirty with the uncommitted 001P increment

## Status Summary

| Area | Status | Evidence |
|---|---|---|
| Repository integrity | Pass | `git diff --check` clean |
| Compose configuration | Pass | `docker compose config --quiet` |
| Docker engine startup | Pass | Linux engine 29.5.3 |
| Docker image build | Pass | Backend and frontend images built successfully |
| Container startup | Pass | PostgreSQL and Redis healthy; backend, frontend, and Nginx running |
| Database migrations | Pass | PostgreSQL at `0008_notification_framework (head)` |
| Backend startup | Pass | `/health` and `/ready` returned expected status |
| Backend Ruff | Pass | Containerized `ruff check app tests` |
| Backend tests | Pass | 68 containerized tests passed |
| Frontend tests | Pass | 5 containerized Vitest tests passed |
| Frontend build | Pass | Containerized Next.js 16.2.9 production build |
| Dependency audit | Pass | 0 npm vulnerabilities |
| Live API smoke tests | Pass | All required API groups exercised against PostgreSQL/Redis |

## Migration Status

Alembic applied revisions `0001` through `0008_notification_framework` against PostgreSQL. PostgreSQL validation exposed that the original `0007_workflow_definition_metadata` revision identifier exceeded Alembic's 32-character version column; the identifier was shortened to `0007_workflow_metadata`, and the clean migration chain then passed.

Current revision:

```text
0008_notification_framework (head)
```

## Backend Test Status

All 68 tests passed inside the Linux backend container. The suite includes:

- `test_bpp_seed_installs_registry_definition_config_permissions`
- `test_bpp_workflow_happy_path_completes`
- `test_bpp_invalid_transition_rejected`
- `test_bpp_missing_permission_rejected`
- `test_bpp_approval_policy_executive_threshold`
- `test_bpp_notification_emit_creates_event`
- `test_bpp_snapshots_written_for_workflow_events`
- `test_bpp_registry_entry_matches_active_definition`
- Inactive registry enforcement
- Full release seed/bootstrap idempotency

## Frontend Test Status

- Five Vitest tests passed in the frontend container.
- The Next.js production build passed under Node 20.
- Local ESLint and explicit TypeScript checks passed.
- npm audit reported zero vulnerabilities.

## API Smoke Test Results

| API group | Result |
|---|---|
| Health and readiness | Pass: `ok` / `ready` |
| Admin bootstrap | Pass: administrator created |
| Login and current user | Pass: token issued and authenticated identity returned |
| Configuration seed/list | Pass: four platform defaults seeded and listed |
| Workflow registry seed/list/detail | Pass: three entries; `BPP_PURCHASING` resolved |
| BPP definition seed | Pass: version 1 installed |
| Workflow start/actions | Pass: instance started and completed |
| Approval policy seed/evaluate | Pass: six defaults; executive result at 75000 |
| Notification seed/emit/history | Pass: eight templates; in-app event queued and listed |
| Snapshot history | Pass: 14 snapshots returned for the live happy-path entity |

API-submitted workflow, approval, and notification actor values were replaced by authenticated identity where required.

## End-to-End BPP Scenario

The authenticated live scenario passed against the Compose stack:

1. Seed platform configuration and workflow registry.
2. Seed BPP definition, permissions, and configuration.
3. Seed approval policy defaults.
4. Seed notification defaults and eight templates.
5. Bootstrap and authenticate the validation administrator.
6. Evaluate a 75000 request as executive approval.
7. Start `BPP_PURCHASING` in `draft`.
8. Execute all eleven happy-path transitions.
9. Confirm final state `completed` and status `complete`.
10. Emit an in-app notification and confirm status `queued`.
11. Confirm notification history and 14 entity snapshots.

## Negative-Path Results

| Scenario | Result |
|---|---|
| Invalid transition | Pass: HTTP 400 |
| Missing transition permission | Pass: HTTP 403 using a roleless authenticated user |
| Completed workflow advancement | Pass: HTTP 400 |
| Inactive registry entry | Pass: integration test rejects engine use |
| Disabled approval policy | Pass: `requires_approval=false`, level `none` |
| Inactive notification template | Pass: status `skipped` |
| Missing/malformed policy configuration | Pass: safe configuration error in integration suite |
| Invalid JSON configuration request | Pass: HTTP 422 |

Temporary approval and template changes used by negative tests were restored.

## Build Hygiene

The initial frontend build transferred approximately 500 MB because local `node_modules` and `.next` were included. Scoped backend and frontend `.dockerignore` files were added. The repeat build passed with approximately 18 KB backend and 2 KB frontend contexts.

## Release Hardening Validation

The production Compose override was built and started successfully. Inspection confirmed:

- Backend command: `uvicorn app.main:app --host 0.0.0.0 --port 8000` without reload
- Frontend command: `npm run start -- -H 0.0.0.0` using the image's prebuilt Next.js artifact
- No backend or frontend source bind mounts
- Health `ok`, readiness `ready`, and Nginx HTTP 200
- 68 backend tests, Ruff, and 5 frontend tests passed in production-mode containers
- Five-service log review found no current error, panic, traceback, or connection-refused entries

## Known Issues

1. The validated changes are not committed, so the recorded SHA identifies the pre-001P base rather than an immutable release candidate. Commit before release or deployment.
2. Email and webhook delivery are intentionally adapter stubs in 001P.4; email queues and disabled webhook delivery skips by contract.
3. The generated local `.env` uses development secrets and must not be used for production deployment.

No known issue blocks continued package development.

## Go/No-Go Decision

**GO. 001P is accepted for continued development.**

All required migrations, container builds, service startups, backend/frontend tests, live API smoke tests, end-to-end workflow execution, snapshots, notification behavior, policy evaluation, and permission failures passed.
