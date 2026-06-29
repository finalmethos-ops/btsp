# Vendor Integration Platform

## Boundary

Epic 001T begins where the Purchase Order Engine's internal handoff ends. It records and processes
vendor-facing acknowledgements, shipment updates, ASNs, and connector activity without changing the
immutable PO artifact model established by 001S.

The platform separates transport, ingestion, normalization, and domain projection. An API, SFTP
poller, EDI translator, or manual import can therefore produce the same durable inbound envelope.

## Security and secrets

Vendor endpoint records contain only non-secret metadata and an opaque `connection_reference` for
an external secret provider. Passwords, tokens, API keys, private keys, and other connector secrets
must never be stored in endpoint configuration or event snapshots.

The initial ingestion API uses BTSP permission enforcement. Public vendor authentication, request
signatures, replay windows, and connector-specific credentials are follow-on transport work; 001T.1
does not expose an unauthenticated webhook.

## Idempotency

Inbound events are unique by endpoint and external event ID. Replaying identical canonical JSON
returns the original event. Reusing an ID with different type, occurrence time, or payload fails
closed. Every accepted event stores a SHA-256 payload digest and an immutable receipt snapshot.

## Purchase order acknowledgements

Acknowledgements are projections of immutable inbound envelopes, not edits to the source event or
PO artifact. Processing requires a completed internal transmission and exact vendor match. Accepted
with changes and rejected outcomes produce explicit exception states; vendor-proposed changes never
silently rewrite ordered lines or financial values.

## Shipments and ASNs

Shipment updates project vendor-reported transport state onto a durable shipment record. ASNs retain
line-level links to immutable PO lines and reject cumulative quantities above the ordered amount.
Vendor-reported delivery is explicitly not warehouse receipt; receiving remains an independent 001U
control boundary.

## Package progression

1. `001T.1` — endpoint registry and idempotent inbound event envelope.
2. `001T.2` — purchase order acknowledgements and exception projection.
3. `001T.3` — shipment updates and ASN domain model.
4. `001T.4` — connector adapters for API, SFTP, and EDI translation.
5. `001T.5` — import scheduling, retries, dead-letter handling, and operations UI.
6. `001T.6` — security hardening and production validation.

Epic 001T is complete through `001T.6`. Production partner activation remains conditional on a
deployed transport worker, external secret resolution, partner-specific mapping, monitoring, and
vendor acceptance testing; the platform fails closed when those dependencies are absent.
