from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.receiving import PurchaseReceipt, PurchaseReceiptLine
from app.models.store import Store
from app.schemas.invoice import VendorInvoiceCreate, VendorInvoiceLineCreate
from app.schemas.reconciliation import (
    ReconciliationDecision,
    ReconciliationExceptionResolution,
)
from app.services.invoice_service import InvoiceError, create_vendor_invoice
from app.services.reconciliation_service import (
    ReconciliationError,
    create_reconciliation,
    decide_reconciliation,
    resolve_reconciliation_exception,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                CatalogVendor(
                    vendor_code="V-INV", name="Invoice Vendor", is_active=True, source_file="test"
                ),
                CatalogVendor(
                    vendor_code="V-OTHER", name="Other Vendor", is_active=True, source_file="test"
                ),
                Store(store_number="001", name="Store", region_code="EAST", is_active=True),
            ]
        )
        session.commit()
        yield session


def _order_with_receipt(db: Session) -> tuple[PurchaseOrder, PurchaseOrderLine]:
    order = PurchaseOrder(
        po_number="PO-INV-1",
        workflow_code="BPP_PURCHASING",
        vendor_code="V-INV",
        status="received",
        currency="USD",
        subtotal=20,
        freight_total=0,
        tax_total=0,
        total=20,
        created_by="buyer@example.com",
    )
    line = PurchaseOrderLine(
        source_request_id="request-1",
        source_line_id=1,
        store_number="001",
        product_code="SKU-1",
        product_name="Product",
        quantity=2,
        unit_price=10,
        freight_amount=0,
        tax_amount=0,
        extended_amount=20,
    )
    order.lines.append(line)
    db.add(order)
    db.flush()
    receipt = PurchaseReceipt(
        receipt_number="RCV-2026-000001",
        purchase_order_id=order.id,
        store_number="001",
        receipt_sha256="a" * 64,
        status="posted",
        received_at=datetime(2026, 6, 28, tzinfo=UTC),
        received_by="receiver@example.com",
    )
    receipt.lines.append(
        PurchaseReceiptLine(
            purchase_order_line_id=line.id,
            product_code=line.product_code,
            received_quantity=2,
            accepted_quantity=2,
            rejected_quantity=0,
        )
    )
    db.add(receipt)
    db.commit()
    db.refresh(order)
    return order, line


def _payload(order: PurchaseOrder, line: PurchaseOrderLine) -> VendorInvoiceCreate:
    return VendorInvoiceCreate(
        invoice_number="INV-001",
        vendor_code="V-INV",
        purchase_order_id=order.id,
        invoice_date=datetime(2026, 6, 28, tzinfo=UTC),
        currency="USD",
        subtotal=20,
        freight_total=0,
        tax_total=0,
        total=20,
        lines=[
            VendorInvoiceLineCreate(
                line_number=1,
                purchase_order_line_id=line.id,
                product_code="SKU-1",
                quantity=2,
                unit_price=10,
                extended_amount=20,
            )
        ],
    )


def test_invoice_matches_order_and_receipt_and_is_idempotent(db: Session) -> None:
    order, line = _order_with_receipt(db)
    payload = _payload(order, line)

    invoice, created = create_vendor_invoice(db, payload, "ap@example.com")
    repeated, repeated_created = create_vendor_invoice(db, payload, "ap@example.com")

    assert created is True
    assert repeated_created is False
    assert repeated.id == invoice.id
    assert invoice.status == "matched"
    assert invoice.lines[0].match.status == "matched"
    assert invoice.lines[0].match.accepted_quantity == Decimal("2")
    assert invoice.lines[0].match.quantity_difference == 0
    assert invoice.lines[0].match.price_difference == 0


def test_invoice_quantity_and_price_differences_are_explicit(db: Session) -> None:
    order, line = _order_with_receipt(db)
    payload = _payload(order, line)
    payload.lines[0].quantity = Decimal("1")
    payload.lines[0].unit_price = Decimal("12")
    payload.lines[0].extended_amount = Decimal("12")
    payload.subtotal = Decimal("12")
    payload.total = Decimal("12")

    invoice, _created = create_vendor_invoice(db, payload, "ap@example.com")

    match = invoice.lines[0].match
    assert invoice.status == "match_exception"
    assert match.quantity_difference == Decimal("-1")
    assert match.price_difference == Decimal("2")


def test_invoice_number_conflict_and_vendor_mismatch_fail_closed(db: Session) -> None:
    order, line = _order_with_receipt(db)
    payload = _payload(order, line)
    create_vendor_invoice(db, payload, "ap@example.com")
    changed = payload.model_copy(deep=True)
    changed.tax_total = Decimal("1")
    changed.total = Decimal("21")
    with pytest.raises(InvoiceError, match="different invoice content"):
        create_vendor_invoice(db, changed, "ap@example.com")

    other = payload.model_copy(deep=True)
    other.invoice_number = "INV-OTHER"
    other.vendor_code = "V-OTHER"
    with pytest.raises(InvoiceError, match="vendor does not match"):
        create_vendor_invoice(db, other, "ap@example.com")


def test_invoice_arithmetic_is_exact() -> None:
    with pytest.raises(ValidationError, match="extended amount"):
        VendorInvoiceLineCreate(
            line_number=1,
            purchase_order_line_id=1,
            product_code="SKU",
            quantity=2,
            unit_price=10,
            extended_amount=19,
        )


def test_clean_reconciliation_is_idempotent_and_approvable(db: Session) -> None:
    order, line = _order_with_receipt(db)
    invoice, _created = create_vendor_invoice(db, _payload(order, line), "ap@example.com")

    case, created = create_reconciliation(db, invoice.id, "analyst@example.com")
    repeated, repeated_created = create_reconciliation(db, invoice.id, "analyst@example.com")

    assert created is True
    assert repeated_created is False
    assert repeated.id == case.id
    assert case.status == "ready_for_approval"
    assert case.exceptions == []
    approved = decide_reconciliation(
        db,
        case.id,
        ReconciliationDecision(action="approve", note="Three-way match complete"),
        "manager@example.com",
    )
    db.refresh(invoice)
    assert approved.status == "approved"
    assert invoice.status == "approved_for_payment"
    with pytest.raises(ReconciliationError, match="final decision"):
        decide_reconciliation(
            db,
            case.id,
            ReconciliationDecision(action="reject", note="Too late"),
            "manager@example.com",
        )


@pytest.mark.parametrize("actor", ["ap@example.com", "analyst@example.com"])
def test_reconciliation_approval_enforces_separation_of_duties(db: Session, actor: str) -> None:
    order, line = _order_with_receipt(db)
    invoice, _created = create_vendor_invoice(db, _payload(order, line), "ap@example.com")
    case, _case_created = create_reconciliation(db, invoice.id, "analyst@example.com")

    with pytest.raises(ReconciliationError, match="requires an actor independent"):
        decide_reconciliation(
            db,
            case.id,
            ReconciliationDecision(action="approve", note="Self approval attempt"),
            actor,
        )


def test_reconciliation_requires_every_exception_to_be_dispositioned(db: Session) -> None:
    order, line = _order_with_receipt(db)
    payload = _payload(order, line)
    payload.lines[0].quantity = Decimal("1")
    payload.lines[0].unit_price = Decimal("12")
    payload.lines[0].extended_amount = Decimal("12")
    payload.subtotal = Decimal("12")
    payload.total = Decimal("12")
    invoice, _created = create_vendor_invoice(db, payload, "ap@example.com")
    case, _case_created = create_reconciliation(db, invoice.id, "analyst@example.com")

    assert case.status == "exception_review"
    assert {item.exception_type for item in case.exceptions} == {"quantity", "unit_price"}
    with pytest.raises(ReconciliationError, match="Open exceptions"):
        decide_reconciliation(
            db,
            case.id,
            ReconciliationDecision(action="approve", note="Premature"),
            "manager@example.com",
        )
    first = resolve_reconciliation_exception(
        db,
        case.exceptions[0].id,
        ReconciliationExceptionResolution(
            disposition="vendor_credit", note="Credit memo requested"
        ),
        "analyst@example.com",
    )
    assert first.status == "exception_review"
    cleared = resolve_reconciliation_exception(
        db,
        case.exceptions[1].id,
        ReconciliationExceptionResolution(
            disposition="accept_variance", note="Price difference approved"
        ),
        "analyst@example.com",
    )
    assert cleared.status == "ready_for_approval"
    assert all(item.status == "resolved" for item in cleared.exceptions)


def test_reconciliation_can_be_rejected_with_open_exceptions(db: Session) -> None:
    order, line = _order_with_receipt(db)
    payload = _payload(order, line)
    payload.lines[0].quantity = Decimal("1")
    payload.lines[0].extended_amount = Decimal("10")
    payload.subtotal = Decimal("10")
    payload.total = Decimal("10")
    invoice, _created = create_vendor_invoice(db, payload, "ap@example.com")
    case, _created_case = create_reconciliation(db, invoice.id, "analyst@example.com")

    rejected = decide_reconciliation(
        db,
        case.id,
        ReconciliationDecision(action="reject", note="Vendor must issue corrected invoice"),
        "manager@example.com",
    )
    db.refresh(invoice)
    assert rejected.status == "rejected"
    assert invoice.status == "rejected"
