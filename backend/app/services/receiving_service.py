import hashlib
import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrder
from app.models.receiving import PurchaseReceipt, PurchaseReceiptLine, ReceiptSequence
from app.models.store import Store
from app.models.vendor_integration import VendorAdvanceShipNotice, VendorAdvanceShipNoticeLine
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.receiving import PurchaseReceiptCreate
from app.services.receipt_variance_service import detect_receipt_variances
from app.services.snapshot_service import append_snapshot

RECEIVING_ELIGIBLE_STATUSES = {
    "transmitted",
    "vendor_acknowledged",
    "vendor_acknowledged_changes",
    "shipment_planned",
    "shipment_in_transit",
    "shipment_delayed",
    "shipment_delivered",
    "partially_received",
    "received",
}


class ReceivingError(ValueError):
    pass


def _payload_hash(payload: PurchaseReceiptCreate) -> str:
    content = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(content).hexdigest()


def allocate_receipt_number(db: Session, at: datetime) -> str:
    prefix = "RCV"
    year = at.year
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"receipt:{prefix}:{year}"},
        )
    sequence = db.scalar(
        select(ReceiptSequence)
        .where(ReceiptSequence.prefix == prefix, ReceiptSequence.sequence_year == year)
        .with_for_update()
    )
    if sequence is None:
        sequence = ReceiptSequence(prefix=prefix, sequence_year=year, next_value=1)
        db.add(sequence)
        db.flush()
    value = sequence.next_value
    sequence.next_value += 1
    return f"{prefix}-{year}-{value:06d}"


def _project_order_status(db: Session, order: PurchaseOrder) -> None:
    accepted_by_line = dict(
        db.execute(
            select(
                PurchaseReceiptLine.purchase_order_line_id,
                func.sum(PurchaseReceiptLine.accepted_quantity),
            )
            .join(PurchaseReceipt)
            .where(
                PurchaseReceipt.purchase_order_id == order.id,
                PurchaseReceipt.status.in_(("posted", "posted_with_exceptions")),
            )
            .group_by(PurchaseReceiptLine.purchase_order_line_id)
        ).all()
    )
    order.status = (
        "received"
        if all(Decimal(accepted_by_line.get(line.id, 0)) >= line.quantity for line in order.lines)
        else "partially_received"
    )


def create_receipt(
    db: Session, payload: PurchaseReceiptCreate, actor: str
) -> tuple[PurchaseReceipt, bool]:
    digest = _payload_hash(payload)
    if payload.external_receipt_id is not None:
        existing = db.scalar(
            select(PurchaseReceipt)
            .options(selectinload(PurchaseReceipt.lines), selectinload(PurchaseReceipt.variances))
            .where(
                PurchaseReceipt.store_number == payload.store_number,
                PurchaseReceipt.external_receipt_id == payload.external_receipt_id,
            )
        )
        if existing is not None:
            if existing.receipt_sha256 != digest:
                raise ReceivingError(
                    "External receipt ID was already used with different receipt content"
                )
            return existing, False

    store = db.scalar(
        select(Store).where(Store.store_number == payload.store_number).with_for_update()
    )
    if store is None or not store.is_active:
        raise ReceivingError("Receiving store is not active")
    order = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == payload.purchase_order_id)
        .with_for_update()
    )
    if order is None:
        raise ReceivingError("Purchase order not found")
    if order.status not in RECEIVING_ELIGIBLE_STATUSES:
        raise ReceivingError("Purchase order is not eligible for receiving")
    lines_by_id = {line.id: line for line in order.lines}

    asn_lines: dict[int, VendorAdvanceShipNoticeLine] = {}
    if payload.asn_id is not None:
        asn = db.get(VendorAdvanceShipNotice, payload.asn_id)
        if asn is None or asn.purchase_order_id != order.id:
            raise ReceivingError("ASN does not belong to this purchase order")
        asn_lines = {
            line.purchase_order_line_id: line
            for line in db.scalars(
                select(VendorAdvanceShipNoticeLine).where(
                    VendorAdvanceShipNoticeLine.asn_id == asn.id
                )
            ).all()
        }

    receipt = PurchaseReceipt(
        receipt_number=allocate_receipt_number(db, payload.received_at),
        purchase_order_id=order.id,
        asn_id=payload.asn_id,
        store_number=payload.store_number,
        external_receipt_id=payload.external_receipt_id,
        receipt_sha256=digest,
        status="posted",
        packing_slip_number=payload.packing_slip_number,
        notes=payload.notes,
        received_at=payload.received_at,
        received_by=actor,
    )
    for item in payload.lines:
        order_line = lines_by_id.get(item.purchase_order_line_id)
        if order_line is None:
            raise ReceivingError("Receipt line does not belong to this purchase order")
        if order_line.store_number != payload.store_number:
            raise ReceivingError("Receipt line does not belong to the receiving store")
        asn_line = asn_lines.get(order_line.id) if payload.asn_id is not None else None
        if payload.asn_id is not None and asn_line is None:
            raise ReceivingError("Receipt line is not present on the selected ASN")
        receipt.lines.append(
            PurchaseReceiptLine(
                purchase_order_line_id=order_line.id,
                asn_line_id=asn_line.id if asn_line is not None else None,
                product_code=order_line.product_code,
                received_quantity=item.received_quantity,
                accepted_quantity=item.accepted_quantity,
                rejected_quantity=item.rejected_quantity,
                rejection_reason=item.rejection_reason,
                lot_number=item.lot_number,
            )
        )
    db.add(receipt)
    db.flush()
    detect_receipt_variances(db, receipt)
    _project_order_status(db, order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ReceivingError("Receipt conflicts with an existing receiving record") from exc
    db.refresh(receipt)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="receiving.receipt_posted",
            entity_type="purchase_receipt",
            entity_id=receipt.id,
            actor=actor,
            payload={
                "receipt_number": receipt.receipt_number,
                "purchase_order_id": order.id,
                "store_number": receipt.store_number,
                "line_count": len(receipt.lines),
                "variance_count": len(receipt.variances),
                "receipt_sha256": receipt.receipt_sha256,
            },
        ),
    )
    return receipt, True


def list_receipts(
    db: Session, purchase_order_id: str | None = None, store_number: str | None = None
) -> list[PurchaseReceipt]:
    statement = (
        select(PurchaseReceipt)
        .options(selectinload(PurchaseReceipt.lines), selectinload(PurchaseReceipt.variances))
        .order_by(PurchaseReceipt.received_at.desc())
    )
    if purchase_order_id is not None:
        statement = statement.where(PurchaseReceipt.purchase_order_id == purchase_order_id)
    if store_number is not None:
        statement = statement.where(PurchaseReceipt.store_number == store_number)
    return list(db.scalars(statement).all())


def get_receipt(db: Session, receipt_id: str) -> PurchaseReceipt | None:
    return db.scalar(
        select(PurchaseReceipt)
        .options(selectinload(PurchaseReceipt.lines), selectinload(PurchaseReceipt.variances))
        .where(PurchaseReceipt.id == receipt_id)
    )
