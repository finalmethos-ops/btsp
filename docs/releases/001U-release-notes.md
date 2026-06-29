# Epic 001U Release Notes — Receiving and Reconciliation

## Delivered

- Store-scoped physical receipt ledger with PO and ASN linkage.
- Exact accepted/rejected quantity accounting and canonical WMS replay protection.
- Durable order, ASN, and rejected-quantity variances with resolution workflow.
- Variance-linked backorders with partial fulfillment, cancellation, and substitution.
- Immutable vendor invoices with deterministic PO/receipt line matching.
- Three-way reconciliation cases, exception dispositions, and payment-approval decisions.
- Receiving and invoice/reconciliation workspaces.
- Least-privilege receiving and AP roles plus enforced separation of duties.
- Cross-ledger integrity audit and production operations runbook.

## Database

Epic 001U spans migrations `0022_receiving_foundation` through `0026_reconciliation`.

## Boundaries

- Vendor delivery remains distinct from physical receipt.
- Physical receipt, invoice, and decision evidence is append-oriented and auditable.
- Approval does not transmit payment or post accounting entries.
- Direct database correction is not an operational workflow.

## Next epic

001V introduces inventory and analytics: operational dashboards, KPI reporting, spend analysis, vendor scorecards, approval analytics, and workflow metrics.
