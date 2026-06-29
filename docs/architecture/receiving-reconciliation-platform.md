# Receiving and Reconciliation Platform

## Boundary

Epic 001U begins when goods physically arrive. Vendor shipment and ASN records are advisory logistics data; they never constitute warehouse receipt. A posted BTSP receipt is the authoritative record of quantities physically received, accepted, and rejected at a specific store.

Consolidated purchase orders may contain lines for multiple stores. Receipt headers are therefore store-scoped, and every posted line must belong to both the selected purchase order and receiving store.

## Package progression

1. `001U.1` — receiving ledger, quantity accounting, ASN linkage, and PO receipt projection.
2. `001U.2` — ordered/ASN/received variance detection and exception classification.
3. `001U.3` — backorders, shortages, substitutions, and resolution workflow.
4. `001U.4` — vendor invoice ingestion and line-level matching.
5. `001U.5` — three-way reconciliation and exception workflows.
6. `001U.6` — operational UI, security hardening, and production validation.

Epic 001U is complete through `001U.6`. Downstream accounting/payment transport remains a separate
deployment integration and must consume only explicitly approved reconciliation outcomes.

## Ledger principles

- Posted receipts are append-only evidence; corrections use explicit future reversal/adjustment records.
- Accepted plus rejected quantity must exactly equal physical received quantity.
- External WMS receipt IDs are idempotent within a store and conflict when reused with different content.
- Overages remain recordable so variance workflows see physical reality.
- PO status is a projection of cumulative accepted quantity, not vendor-reported delivery.
