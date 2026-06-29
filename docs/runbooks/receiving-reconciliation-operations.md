# Receiving and Reconciliation Operations Runbook

## Daily checks

- Review receipts in `posted_with_exceptions` and aged open variances.
- Review open/partially fulfilled backorders and overdue expected dates.
- Review invoice `match_exception` cases and unresolved vendor-credit requests.
- Review reconciliation cases awaiting approval and rejected invoices awaiting correction.
- Run `python -m scripts.validate_001u_integrity` from the backend application directory.

## Receipt incidents

Do not edit posted receipt rows. Preserve the physical evidence and route discrepancies through variance/backorder workflow. Until an explicit reversal package is delivered, escalate erroneous posted receipts to platform operations for controlled investigation rather than direct database correction.

## Invoice incidents

Do not reuse a vendor invoice number with changed content. Reject the incorrect invoice and ingest a vendor-issued corrected invoice with its own invoice number. Never resolve an exception merely to unlock approval; the disposition note must identify the actual credit, correction, or authorized variance decision.

## Access review

- Receiving users must have an active, correct home store.
- AP clerks must not receive `reconciliation.manage`.
- AP approvers must not receive `invoices.manage`.
- Review system-administrator assignments separately and keep them exceptional.

## Downstream payment handoff

Export only invoices in `approved_for_payment`. Use invoice ID and reconciliation ID as idempotency references. Record downstream acknowledgement externally until a supported accounting-export package is introduced. A transport success must not be inferred from BTSP approval alone.
