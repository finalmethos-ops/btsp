import hashlib
import json
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrder
from app.models.receiving import (
    InvoiceLineMatch,
    PurchaseReceipt,
    PurchaseReceiptLine,
    VendorInvoice,
    VendorInvoiceLine,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.invoice import VendorInvoiceCreate
from app.services.snapshot_service import append_snapshot


class InvoiceError(ValueError):
    pass


def _hash(payload: VendorInvoiceCreate) -> str:
    content = json.dumps(
        payload.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(content).hexdigest()


def _invoice_query():
    return select(VendorInvoice).options(
        selectinload(VendorInvoice.lines).selectinload(VendorInvoiceLine.match)
    )


def create_vendor_invoice(
    db: Session, payload: VendorInvoiceCreate, actor: str
) -> tuple[VendorInvoice, bool]:
    digest = _hash(payload)
    existing = db.scalar(
        _invoice_query().where(
            VendorInvoice.vendor_code == payload.vendor_code,
            VendorInvoice.invoice_number == payload.invoice_number,
        )
    )
    if existing is not None:
        if existing.invoice_sha256 != digest:
            raise InvoiceError("Invoice number was already used with different invoice content")
        return existing, False
    order = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == payload.purchase_order_id)
        .with_for_update()
    )
    if order is None:
        raise InvoiceError("Purchase order not found")
    if order.vendor_code != payload.vendor_code:
        raise InvoiceError("Invoice vendor does not match purchase order vendor")
    if order.currency != payload.currency.upper():
        raise InvoiceError("Invoice currency does not match purchase order currency")
    if order.status in {"created", "prepared", "cancelled"}:
        raise InvoiceError("Purchase order is not eligible for invoicing")
    order_lines = {line.id: line for line in order.lines}
    invoice = VendorInvoice(
        invoice_number=payload.invoice_number,
        vendor_code=payload.vendor_code,
        purchase_order_id=order.id,
        invoice_sha256=digest,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency.upper(),
        subtotal=payload.subtotal,
        freight_total=payload.freight_total,
        tax_total=payload.tax_total,
        total=payload.total,
        status="matched",
        received_by=actor,
    )
    for item in payload.lines:
        order_line = order_lines.get(item.purchase_order_line_id)
        if order_line is None:
            raise InvoiceError("Invoice line does not belong to this purchase order")
        if order_line.product_code != item.product_code:
            raise InvoiceError("Invoice product does not match purchase order line")
        accepted = db.scalar(
            select(func.sum(PurchaseReceiptLine.accepted_quantity))
            .join(PurchaseReceipt)
            .where(
                PurchaseReceiptLine.purchase_order_line_id == order_line.id,
                PurchaseReceipt.status.in_(("posted", "posted_with_exceptions")),
            )
        ) or Decimal("0")
        quantity_difference = item.quantity - accepted
        price_difference = item.unit_price - order_line.unit_price
        match_status = (
            "matched" if quantity_difference == 0 and price_difference == 0 else "exception"
        )
        line = VendorInvoiceLine(
            line_number=item.line_number,
            purchase_order_line_id=order_line.id,
            product_code=item.product_code,
            quantity=item.quantity,
            unit_price=item.unit_price,
            extended_amount=item.extended_amount,
        )
        line.match = InvoiceLineMatch(
            ordered_quantity=order_line.quantity,
            accepted_quantity=accepted,
            invoiced_quantity=item.quantity,
            quantity_difference=quantity_difference,
            ordered_unit_price=order_line.unit_price,
            invoiced_unit_price=item.unit_price,
            price_difference=price_difference,
            status=match_status,
        )
        invoice.lines.append(line)
        if match_status == "exception":
            invoice.status = "match_exception"
    db.add(invoice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise InvoiceError("Invoice conflicts with an existing record") from exc
    db.refresh(invoice)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="reconciliation.invoice_received",
            entity_type="vendor_invoice",
            entity_id=invoice.id,
            actor=actor,
            payload={
                "invoice_number": invoice.invoice_number,
                "vendor_code": invoice.vendor_code,
                "purchase_order_id": invoice.purchase_order_id,
                "status": invoice.status,
                "invoice_sha256": invoice.invoice_sha256,
            },
        ),
    )
    return invoice, True


def list_vendor_invoices(
    db: Session, vendor_code: str | None = None, status: str | None = None
) -> list[VendorInvoice]:
    statement = _invoice_query().order_by(VendorInvoice.invoice_date.desc())
    if vendor_code is not None:
        statement = statement.where(VendorInvoice.vendor_code == vendor_code)
    if status is not None:
        statement = statement.where(VendorInvoice.status == status)
    return list(db.scalars(statement).all())


def get_vendor_invoice(db: Session, invoice_id: str) -> VendorInvoice | None:
    return db.scalar(_invoice_query().where(VendorInvoice.id == invoice_id))
