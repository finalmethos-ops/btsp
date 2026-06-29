# Administration Platform

## Boundary

Epic 001W provides governed administration over BTSP identity, configuration, workflow, notification, health, and audit capabilities. Administrative interfaces call the same permission-checked domain APIs as every other client; they do not bypass service invariants or edit database records directly.

## Package progression

1. `001W.1` — role management and permission assignment.
2. `001W.2` — workflow administration.
3. `001W.3` — notification administration.
4. `001W.4` — system health and operational diagnostics.
5. `001W.5` — unified audit reporting and export.
6. `001W.6` — administration security and BTSP v1.0 production validation.

User management and configuration editing were established by the platform-foundation packages and are incorporated into this administration surface rather than rebuilt.

## Governance principles

- System roles are release-managed and immutable through the runtime API.
- Custom roles use existing registered permissions; arbitrary permission creation is not allowed.
- Assigned roles cannot be deleted.
- Administrative mutations emit durable audit snapshots with actor attribution.
- Administrative navigation and API authorization use the same permission catalog.
