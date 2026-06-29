# Implementation Package 001Q — Independent Purchasing Workflow Platform

## Objective

Install the production workflow platform for independently owned franchise purchasing while preserving strict separation from BPP purchasing.

## Scope

This epic adds:

- `IND_PURCHASING` registry entry with governed Testing lifecycle
- Independent Purchasing definition version 1 with sixteen states
- Happy, revision, rejection, cancellation, expiration, and administrative-reopen transitions
- Eight Independent workflow permissions and role assignments
- Region/store authority enforcement at API start
- Seven workflow configuration defaults
- Eight Independent approval policy defaults and shared evaluator dispatch
- Nine Independent notification templates using the shared framework
- One idempotent installer for every Independent artifact
- Shared permission-seeding abstraction used by platform installers
- Full execution, policy, notification, configuration, permission, snapshot, lock, reopen, idempotency, and BPP regression tests

## Shared Purchasing Platform

001Q introduces no second workflow, approval, notification, configuration, identity, or snapshot engine. BPP and Independent purchasing share infrastructure contracts and seed helpers while retaining distinct definitions, scopes, permissions, policies, templates, and business ownership.

A shared purchase-request persistence model remains deferred until concrete cross-workflow entity requirements are defined; inventing one in this epic would couple workflows to an unapproved data contract.

## Installer

`POST /api/v1/workflow-engine/seeds/ind-purchasing`

Required permission: `configuration.manage`.

The installer verifies the registry entry and upserts permissions, definition, workflow configuration, approval policies, and notification templates without duplicates.

## Architecture Rules Supported

- Official Store Database validates Independent store and region scope.
- Independent and BPP artifacts remain separate.
- Thresholds, restrictions, and notification channels are configuration-backed.
- Workflow, policy, configuration, and notification evidence uses immutable snapshots.
- Authentication is shared; authorization uses Independent permissions.
- Definitions remain versioned and running instances pinned.

## Validation

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml config
docker compose -f docker-compose.yml -f docker-compose.production.yml build
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend pytest
docker compose -f docker-compose.yml -f docker-compose.production.yml exec backend ruff check app tests
docker compose -f docker-compose.yml -f docker-compose.production.yml exec frontend npm run build
docker compose -f docker-compose.yml -f docker-compose.production.yml exec frontend npm test -- --run
```

## Definition of Done

- Workflow registers and seeds idempotently.
- Happy path completes and alternate paths enforce permissions.
- Approval policies respond to persisted configuration changes.
- Notifications use shared configuration and persistence.
- Snapshots cover workflow events.
- Region/store scope is enforced.
- Completed instances remain locked; approved terminal instances can be administratively reopened.
- Existing BPP tests remain green.
- All production-mode container validation passes.
