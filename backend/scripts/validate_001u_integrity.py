import json
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.receiving import (
    InvoiceReconciliation,
    PurchaseBackorder,
    PurchaseReceiptLine,
    VendorInvoice,
)


def main() -> None:
    with SessionLocal() as db:
        receipt_lines = list(db.scalars(select(PurchaseReceiptLine)).all())
        backorders = list(db.scalars(select(PurchaseBackorder)).all())
        invoices = list(db.scalars(select(VendorInvoice)).all())
        invoices_by_id = {invoice.id: invoice for invoice in invoices}
        reconciliations = list(db.scalars(select(InvoiceReconciliation)).all())

        invalid_receipt_lines = [
            line.id
            for line in receipt_lines
            if line.accepted_quantity + line.rejected_quantity != line.received_quantity
        ]
        invalid_backorders = [
            item.id
            for item in backorders
            if item.outstanding_quantity < 0
            or item.fulfilled_quantity < 0
            or (
                item.status in {"open", "partially_fulfilled", "fulfilled"}
                and item.fulfilled_quantity + item.outstanding_quantity != item.original_quantity
            )
            or (item.status in {"cancelled", "substituted"} and item.outstanding_quantity != 0)
        ]
        invalid_invoices = [
            invoice.id
            for invoice in invoices
            if sum((line.extended_amount for line in invoice.lines), Decimal("0"))
            != invoice.subtotal
            or invoice.subtotal + invoice.freight_total + invoice.tax_total != invoice.total
            or any(
                line.quantity * line.unit_price != line.extended_amount for line in invoice.lines
            )
        ]
        invalid_approvals = [
            case.id
            for case in reconciliations
            if case.status == "approved"
            and (
                any(item.status == "open" for item in case.exceptions)
                or case.approved_by is None
                or case.approved_by == case.created_by
                or case.invoice_id not in invoices_by_id
                or case.approved_by == invoices_by_id[case.invoice_id].received_by
                or invoices_by_id[case.invoice_id].status != "approved_for_payment"
            )
        ]

        assert not invalid_receipt_lines, "Receipt quantity accounting invariant failed"
        assert not invalid_backorders, "Backorder quantity invariant failed"
        assert not invalid_invoices, "Invoice arithmetic invariant failed"
        assert not invalid_approvals, "Reconciliation approval invariant failed"

        print(
            json.dumps(
                {
                    "approved_reconciliation_count": sum(
                        item.status == "approved" for item in reconciliations
                    ),
                    "backorder_count": len(backorders),
                    "invoice_count": len(invoices),
                    "receipt_line_count": len(receipt_lines),
                    "reconciliation_count": len(reconciliations),
                    "status": "ok",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
