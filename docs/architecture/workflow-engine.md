# Workflow Engine Foundation

BTSP uses a reusable workflow engine for state-based business processes.

Only workflow codes declared by the code-owned workflow registry can be used for definitions and instances. The registry identifies deployable workflow capabilities; this engine owns their versioned runtime state machines.

## Core Concepts

- Workflow definitions describe the process code, version, initial state, terminal states, and allowed rules.
- Workflow instances track a specific entity moving through a definition.
- Actions move an instance from one state to another only when a matching rule exists.
- Rules can require permission codes.
- Workflow activity writes append-only snapshots.

## Current API

- `POST /api/v1/workflow-engine/definitions`
- `POST /api/v1/workflow-engine/instances`
- `POST /api/v1/workflow-engine/instances/{instance_id}/actions`

## Rules

- Definitions are versioned.
- Instances retain the definition version they started with.
- Instance advancement resolves the exact recorded definition version, even after newer versions are activated.
- Completed instances cannot be advanced.
- Invalid actions are rejected.
- Required permissions are checked before state changes.
- BPP and Independent workflows should use separate definition codes.
