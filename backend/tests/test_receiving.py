from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.models.event_snapshot import EventSnapshot
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.receiving import PurchaseReceipt, ReceiptVariance
from app.models.store import Store
from app.schemas.receiving import (
    PurchaseBackorderAction,
    PurchaseBackorderCreate,
    PurchaseReceiptCreate,
    PurchaseReceiptLineCreate,
    ReceiptVarianceResolution,
)
from app.services.backorder_service import (
    BackorderError,
    apply_backorder_action,
    create_backorder,
)
from app.services.receipt_variance_service import (
    ReceiptVarianceError,
    resolve_receipt_variance,
)
from app.services.receiving_service import ReceivingError, create_receipt


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                CatalogVendor(
                    vendor_code="V-RCV",
                    name="Receiving Vendor",
                    is_active=True,
                    source_file="test.xlsx",
                ),
                Store(
                    store_number="001",
                    name="Receiving Store",
                    region_code="EAST",
                    is_active=True,
                ),
                Store(
                    store_number="002",
                    name="Other Store",
                    region_code="EAST",
                    is_active=True,
                ),
            ]
        )
        session.commit()
        yield session


def _order(db: Session) -> PurchaseOrder:
    order = PurchaseOrder(
        po_number="PO-RCV-001",
        workflow_code="BPP_PURCHASING",
        vendor_code="V-RCV",
        status="transmitted",
        currency="USD",
        subtotal=40,
        freight_total=0,
        tax_total=0,
        total=40,
        created_by="buyer@example.com",
    )
    order.lines.extend(
        [
            PurchaseOrderLine(
                source_request_id="request-1",
                source_line_id=1,
                store_number="001",
                product_code="SKU-1",
                product_name="One",
                quantity=2,
                unit_price=10,
                freight_amount=0,
                tax_amount=0,
                extended_amount=20,
            ),
            PurchaseOrderLine(
                source_request_id="request-1",
                source_line_id=2,
                store_number="001",
                product_code="SKU-2",
                product_name="Two",
                quantity=2,
                unit_price=10,
                freight_amount=0,
                tax_amount=0,
                extended_amount=20,
            ),
        ]
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _payload(
    order: PurchaseOrder,
    line_id: int,
    external_id: str = "WMS-001",
    quantity: Decimal = Decimal("2"),
) -> PurchaseReceiptCreate:
    return PurchaseReceiptCreate(
        purchase_order_id=order.id,
        store_number="001",
        external_receipt_id=external_id,
        packing_slip_number="PACK-1",
        received_at=datetime(2026, 6, 28, 12, tzinfo=UTC),
        lines=[
            PurchaseReceiptLineCreate(
                purchase_order_line_id=line_id,
                received_quantity=quantity,
                accepted_quantity=quantity,
                rejected_quantity=0,
            )
        ],
    )


def test_receipts_are_idempotent_audited_and_project_order_status(db: Session) -> None:
    order = _order(db)
    first, created = create_receipt(db, _payload(order, order.lines[0].id), "receiver@example.com")
    repeated, repeated_created = create_receipt(
        db, _payload(order, order.lines[0].id), "receiver@example.com"
    )

    db.refresh(order)
    assert created is True
    assert repeated_created is False
    assert repeated.id == first.id
    assert first.receipt_number == "RCV-2026-000001"
    assert order.status == "partially_received"
    assert db.scalar(select(func.count()).select_from(PurchaseReceipt)) == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(EventSnapshot.event_type == "receiving.receipt_posted")
        )
        == 1
    )

    create_receipt(
        db,
        _payload(order, order.lines[1].id, external_id="WMS-002"),
        "receiver@example.com",
    )
    db.refresh(order)
    assert order.status == "received"


def test_external_receipt_conflict_fails_closed(db: Session) -> None:
    order = _order(db)
    create_receipt(db, _payload(order, order.lines[0].id), "receiver@example.com")

    with pytest.raises(ReceivingError, match="different receipt content"):
        create_receipt(
            db,
            _payload(order, order.lines[1].id),
            "receiver@example.com",
        )


def test_receipt_rejects_cross_store_and_ineligible_order(db: Session) -> None:
    order = _order(db)
    payload = _payload(order, order.lines[0].id)
    payload.store_number = "002"
    with pytest.raises(ReceivingError, match="receiving store"):
        create_receipt(db, payload, "receiver@example.com")

    order.status = "created"
    db.commit()
    with pytest.raises(ReceivingError, match="not eligible"):
        create_receipt(db, _payload(order, order.lines[0].id), "receiver@example.com")


def test_receipt_quantity_accounting_is_exact() -> None:
    with pytest.raises(ValidationError, match="must equal"):
        PurchaseReceiptLineCreate(
            purchase_order_line_id=1,
            received_quantity=2,
            accepted_quantity=1,
            rejected_quantity=0,
        )
    with pytest.raises(ValidationError, match="requires a reason"):
        PurchaseReceiptLineCreate(
            purchase_order_line_id=1,
            received_quantity=2,
            accepted_quantity=1,
            rejected_quantity=1,
        )


def test_order_overage_creates_durable_variance_and_resolution(db: Session) -> None:
    order = _order(db)
    receipt, _created = create_receipt(
        db,
        _payload(order, order.lines[0].id, quantity=Decimal("3")),
        "receiver@example.com",
    )

    assert receipt.status == "posted_with_exceptions"
    assert len(receipt.variances) == 1
    variance = receipt.variances[0]
    assert variance.variance_type == "order_overage"
    assert variance.expected_quantity == Decimal("2")
    assert variance.actual_quantity == Decimal("3")
    assert variance.difference_quantity == Decimal("1")
    assert db.scalar(select(func.count()).select_from(ReceiptVariance)) == 1

    resolved = resolve_receipt_variance(
        db,
        variance.id,
        ReceiptVarianceResolution(action="waive", note="Vendor-approved bonus unit"),
        "manager@example.com",
    )
    db.refresh(receipt)
    assert resolved.status == "waived"
    assert receipt.status == "posted"
    with pytest.raises(ReceiptVarianceError, match="already closed"):
        resolve_receipt_variance(
            db,
            variance.id,
            ReceiptVarianceResolution(action="resolve", note="Duplicate attempt"),
            "manager@example.com",
        )


def test_rejected_quantity_creates_exception_variance(db: Session) -> None:
    order = _order(db)
    payload = _payload(order, order.lines[0].id)
    payload.lines[0].accepted_quantity = Decimal("1")
    payload.lines[0].rejected_quantity = Decimal("1")
    payload.lines[0].rejection_reason = "Damaged carton"

    receipt, _created = create_receipt(db, payload, "receiver@example.com")

    assert receipt.status == "posted_with_exceptions"
    assert [item.variance_type for item in receipt.variances] == ["rejected_quantity"]
    assert receipt.variances[0].actual_quantity == Decimal("1")


def _rejected_receipt(db: Session) -> PurchaseReceipt:
    order = _order(db)
    payload = _payload(order, order.lines[0].id)
    payload.lines[0].accepted_quantity = Decimal("1")
    payload.lines[0].rejected_quantity = Decimal("1")
    payload.lines[0].rejection_reason = "Damaged carton"
    return create_receipt(db, payload, "receiver@example.com")[0]


def test_backorder_is_variance_linked_idempotent_and_partially_fulfilled(db: Session) -> None:
    receipt = _rejected_receipt(db)
    variance = receipt.variances[0]
    payload = PurchaseBackorderCreate(
        source_variance_id=variance.id,
        note="Vendor will replace damaged unit",
    )

    backorder, created = create_backorder(db, payload, "manager@example.com")
    repeated, repeated_created = create_backorder(db, payload, "manager@example.com")

    db.refresh(receipt)
    db.refresh(variance)
    assert created is True
    assert repeated_created is False
    assert repeated.id == backorder.id
    assert backorder.backorder_number == "BO-2026-000001"
    assert backorder.original_quantity == Decimal("1")
    assert variance.status == "resolved"
    assert receipt.status == "posted"

    partial = apply_backorder_action(
        db,
        backorder.id,
        PurchaseBackorderAction(action="receive", quantity=Decimal("0.5"), note="First carton"),
        "receiver@example.com",
    )
    assert partial.status == "partially_fulfilled"
    assert partial.outstanding_quantity == Decimal("0.5")
    complete = apply_backorder_action(
        db,
        backorder.id,
        PurchaseBackorderAction(action="receive", quantity=Decimal("0.5"), note="Final carton"),
        "receiver@example.com",
    )
    assert complete.status == "fulfilled"
    assert complete.outstanding_quantity == 0
    assert [event.action for event in complete.events] == ["create", "receive", "receive"]


@pytest.mark.parametrize(
    ("action", "product", "expected_status"),
    [("cancel", None, "cancelled"), ("substitute", "SKU-ALT", "substituted")],
)
def test_backorder_terminal_resolutions(
    db: Session, action: str, product: str | None, expected_status: str
) -> None:
    variance = _rejected_receipt(db).variances[0]
    backorder, _created = create_backorder(
        db,
        PurchaseBackorderCreate(source_variance_id=variance.id, note="Replacement decision"),
        "manager@example.com",
    )

    resolved = apply_backorder_action(
        db,
        backorder.id,
        PurchaseBackorderAction(
            action=action,
            substitute_product_code=product,
            note="Approved resolution",
        ),
        "manager@example.com",
    )
    assert resolved.status == expected_status
    assert resolved.outstanding_quantity == 0
    with pytest.raises(BackorderError, match="already closed"):
        apply_backorder_action(
            db,
            backorder.id,
            PurchaseBackorderAction(action="cancel", note="Duplicate"),
            "manager@example.com",
        )


def test_backorder_rejects_over_fulfillment(db: Session) -> None:
    variance = _rejected_receipt(db).variances[0]
    backorder, _created = create_backorder(
        db,
        PurchaseBackorderCreate(source_variance_id=variance.id, note="Replace"),
        "manager@example.com",
    )
    with pytest.raises(BackorderError, match="exceeds"):
        apply_backorder_action(
            db,
            backorder.id,
            PurchaseBackorderAction(action="receive", quantity=2, note="Too many"),
            "receiver@example.com",
        )
