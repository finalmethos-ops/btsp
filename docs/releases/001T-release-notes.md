# Epic 001T Release Notes — Vendor Integration Platform

## Delivered

- Vendor endpoint registry with opaque credential references.
- Canonical, idempotent inbound event envelopes and immutable audit snapshots.
- Purchase order acknowledgement processing with accepted, changed, and rejected outcomes.
- Shipment updates and advance ship notices linked to immutable PO lines.
- Bounded normalized JSON imports with file-level checksum replay protection.
- Durable schedules, worker leases, retries, dead letters, and operator replay.
- Connector operations dashboard.
- Least-privilege operator and worker permissions.
- Hashed worker leases, defense-in-depth secret detection, production audit tooling, and operations runbook.

## Database

Epic 001T spans migrations `0016_vendor_integrations` through `0021_connector_security`.

## Compatibility and boundaries

- Existing Purchase Order Engine artifacts remain immutable.
- Vendor-reported delivery is not warehouse receipt; receiving begins in 001U.
- Endpoint configuration stores no credentials.
- EDI input is rejected until a certified partner-specific mapping is configured.
- Production transport workers, scheduler supervision, secret resolution, and partner certification remain deployment responsibilities.

## Next epic

001U introduces receiving, variance detection, backorders, invoice matching, reconciliation, and exception workflows using the PO, acknowledgement, shipment, and ASN records established through 001T.
