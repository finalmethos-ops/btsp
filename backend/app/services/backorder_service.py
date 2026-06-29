from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrderLine
from app.models.receiving import (
    BackorderSequence,
    PurchaseBackorder,
    PurchaseBackorderEvent,
    PurchaseReceipt,
    ReceiptVariance,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.receiving import PurchaseBackorderAction, PurchaseBackorderCreate
from app.services.snapshot_service import append_snapshot

BACKORDER_VARIANCE_TYPES = {"asn_shortage", "rejected_quantity"}


class BackorderError(ValueError):
    pass


def allocate_backorder_number(db: Session, at: datetime | None = None) -> str:
    current = at or datetime.now(UTC)
    prefix = "BO"
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"backorder:{prefix}:{current.year}"},
        )
    sequence = db.scalar(
        select(BackorderSequence)
        .where(
            BackorderSequence.prefix == prefix,
            BackorderSequence.sequence_year == current.year,
        )
        .with_for_update()
    )
    if sequence is None:
        sequence = BackorderSequence(prefix=prefix, sequence_year=current.year, next_value=1)
        db.add(sequence)
        db.flush()
    value = sequence.next_value
    sequence.next_value += 1
    return f"{prefix}-{current.year}-{value:06d}"


def create_backorder(
    db: Session, payload: PurchaseBackorderCreate, actor: str
) -> tuple[PurchaseBackorder, bool]:
    existing = db.scalar(
        select(PurchaseBackorder)
        .options(selectinload(PurchaseBackorder.events))
        .where(PurchaseBackorder.source_variance_id == payload.source_variance_id)
    )
    if existing is not None:
        return existing, False
    variance = db.scalar(
        select(ReceiptVariance)
        .where(ReceiptVariance.id == payload.source_variance_id)
        .with_for_update()
    )
    if variance is None:
        raise BackorderError("Receipt variance not found")
    if variance.variance_type not in BACKORDER_VARIANCE_TYPES:
        raise BackorderError("Variance type is not eligible for a backorder")
    if variance.status != "open":
        raise BackorderError("Receipt variance is already closed")
    receipt = db.get(PurchaseReceipt, variance.receipt_id)
    order_line = db.get(PurchaseOrderLine, variance.receipt_line.purchase_order_line_id)
    if receipt is None or order_line is None:
        raise BackorderError("Receipt evidence is incomplete")
    quantity = (
        -variance.difference_quantity
        if variance.variance_type == "asn_shortage"
        else variance.actual_quantity
    )
    if quantity <= 0:
        raise BackorderError("Variance does not contain a positive backorder quantity")
    backorder = PurchaseBackorder(
        backorder_number=allocate_backorder_number(db),
        source_variance_id=variance.id,
        purchase_order_id=receipt.purchase_order_id,
        purchase_order_line_id=order_line.id,
        store_number=receipt.store_number,
        product_code=order_line.product_code,
        original_quantity=quantity,
        fulfilled_quantity=Decimal("0"),
        outstanding_quantity=quantity,
        status="open",
        expected_at=payload.expected_at,
        created_by=actor,
    )
    backorder.events.append(
        PurchaseBackorderEvent(
            action="create",
            from_status="variance_open",
            to_status="open",
            quantity=quantity,
            note=payload.note,
            actor=actor,
        )
    )
    variance.status = "resolved"
    variance.resolution_action = "backorder_created"
    variance.resolution_note = payload.note
    variance.resolved_by = actor
    variance.resolved_at = datetime.now(UTC)
    db.add(backorder)
    db.flush()
    open_variance_count = db.scalar(
        select(func.count())
        .select_from(ReceiptVariance)
        .where(
            ReceiptVariance.receipt_id == receipt.id,
            ReceiptVariance.status == "open",
        )
    )
    if open_variance_count == 0:
        receipt.status = "posted"
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(PurchaseBackorder)
            .options(selectinload(PurchaseBackorder.events))
            .where(PurchaseBackorder.source_variance_id == payload.source_variance_id)
        )
        if existing is not None:
            return existing, False
        raise BackorderError("Backorder conflicts with an existing record") from exc
    db.refresh(backorder)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="receiving.backorder_created",
            entity_type="purchase_backorder",
            entity_id=backorder.id,
            actor=actor,
            payload={
                "backorder_number": backorder.backorder_number,
                "source_variance_id": variance.id,
                "quantity": str(quantity),
                "store_number": receipt.store_number,
            },
        ),
    )
    return backorder, True


def apply_backorder_action(
    db: Session, backorder_id: str, payload: PurchaseBackorderAction, actor: str
) -> PurchaseBackorder:
    backorder = db.scalar(
        select(PurchaseBackorder)
        .options(selectinload(PurchaseBackorder.events))
        .where(PurchaseBackorder.id == backorder_id)
        .with_for_update()
    )
    if backorder is None:
        raise BackorderError("Backorder not found")
    if backorder.status not in {"open", "partially_fulfilled"}:
        raise BackorderError("Backorder is already closed")
    from_status = backorder.status
    quantity = payload.quantity
    if payload.action == "receive":
        assert quantity is not None
        if quantity > backorder.outstanding_quantity:
            raise BackorderError("Received quantity exceeds the outstanding backorder quantity")
        backorder.fulfilled_quantity += quantity
        backorder.outstanding_quantity -= quantity
        backorder.status = (
            "fulfilled" if backorder.outstanding_quantity == 0 else "partially_fulfilled"
        )
    elif payload.action == "cancel":
        backorder.outstanding_quantity = Decimal("0")
        backorder.status = "cancelled"
    else:
        backorder.substitute_product_code = payload.substitute_product_code
        backorder.outstanding_quantity = Decimal("0")
        backorder.status = "substituted"
    backorder.resolution_note = payload.note
    backorder.events.append(
        PurchaseBackorderEvent(
            action=payload.action,
            from_status=from_status,
            to_status=backorder.status,
            quantity=quantity,
            note=payload.note,
            actor=actor,
        )
    )
    db.commit()
    db.refresh(backorder)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type=f"receiving.backorder_{payload.action}",
            entity_type="purchase_backorder",
            entity_id=backorder.id,
            actor=actor,
            payload={"from_status": from_status, "to_status": backorder.status},
        ),
    )
    return backorder


def list_backorders(
    db: Session, status: str | None = None, store_number: str | None = None
) -> list[PurchaseBackorder]:
    statement = (
        select(PurchaseBackorder)
        .options(selectinload(PurchaseBackorder.events))
        .order_by(PurchaseBackorder.created_at.desc())
    )
    if status is not None:
        statement = statement.where(PurchaseBackorder.status == status)
    if store_number is not None:
        statement = statement.where(PurchaseBackorder.store_number == store_number)
    return list(db.scalars(statement).all())
