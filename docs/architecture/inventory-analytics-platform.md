# Inventory and Analytics Platform

## Boundary

Epic 001V provides read-only operational and analytical views over the purchasing, vendor, receiving, invoice, reconciliation, identity, and workflow ledgers. Analytics never mutates source evidence or substitutes a reporting total for a transactional decision.

Currency-denominated metrics remain grouped by currency unless an explicit exchange-rate source and valuation date are introduced.

## Package progression

1. `001V.1` — analytics contracts and operational dashboard.
2. `001V.2` — spend analysis by vendor, store, category, workflow, and period.
3. `001V.3` — vendor delivery, quality, acknowledgement, and invoice scorecards.
4. `001V.4` — approval and workflow performance analytics.
5. `001V.5` — inventory position, exports, and scheduled reporting.
6. `001V.6` — analytics security, performance, and production validation.

## Query principles

- Transactional tables remain the system of record.
- Zero-state responses are stable and valid.
- Monetary aggregation never crosses currencies implicitly.
- Status counts use durable domain state, not UI labels.
- Expensive historical reporting may introduce controlled snapshots/materialized views in later packages.
