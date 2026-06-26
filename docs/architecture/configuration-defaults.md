# Configuration Defaults

BTSP uses seed defaults to establish safe starter behavior for core workflows and guardrails.

## Initial Defaults

- BPP ordering enabled
- Independent ordering enabled
- Multi-store region lock enabled
- Snapshot recording enabled

## Rules

- Defaults are not hard-coded business logic.
- Defaults are stored as configuration entries.
- Changes to configuration entries create snapshots.
- BPP and Independent workflow defaults remain separate.
- Region lock starts enabled unless explicitly changed by configuration.

## Seed Endpoint

`POST /api/v1/configuration/seed-defaults`

The seed endpoint is protected and intended for installation, deployment, or administrative bootstrap workflows.
