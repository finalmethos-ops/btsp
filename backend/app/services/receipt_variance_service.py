from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrderLine
from app.models.receiving import PurchaseReceipt, PurchaseReceiptLine, ReceiptVariance
from app.models.vendor_integration import VendorAdvanceShipNoticeLine
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.receiving import ReceiptVarianceResolution
from app.services.snapshot_service import append_snapshot


class ReceiptVarianceError(ValueError):
    pass


def _add_variance(
    receipt: PurchaseReceipt,
    line: PurchaseReceiptLine,
    variance_type: str,
    severity: str,
    expected: Decimal,
    actual: Decimal,
) -> None:
    receipt.variances.append(
        ReceiptVariance(
            receipt_line=line,
            variance_type=variance_type,
            severity=severity,
            expected_quantity=expected,
            actual_quantity=actual,
            difference_quantity=actual - expected,
            status="open",
        )
    )


def detect_receipt_variances(db: Session, receipt: PurchaseReceipt) -> list[ReceiptVariance]:
    if receipt.variances:
        return receipt.variances
    for line in receipt.lines:
        order_line = db.get(PurchaseOrderLine, line.purchase_order_line_id)
        if order_line is None:
            raise ReceiptVarianceError("Purchase order line no longer exists")
        cumulative_accepted = db.scalar(
            select(func.sum(PurchaseReceiptLine.accepted_quantity))
            .join(PurchaseReceipt)
            .where(
                PurchaseReceiptLine.purchase_order_line_id == order_line.id,
                PurchaseReceipt.status.in_(("posted", "posted_with_exceptions")),
            )
        ) or Decimal("0")
        if cumulative_accepted > order_line.quantity:
            _add_variance(
                receipt,
                line,
                "order_overage",
                "exception",
                order_line.quantity,
                cumulative_accepted,
            )
        if line.rejected_quantity > 0:
            _add_variance(
                receipt,
                line,
                "rejected_quantity",
                "exception",
                Decimal("0"),
                line.rejected_quantity,
            )
        if line.asn_line_id is not None:
            asn_line = db.get(VendorAdvanceShipNoticeLine, line.asn_line_id)
            if asn_line is not None and line.received_quantity != asn_line.quantity:
                variance_type = (
                    "asn_shortage" if line.received_quantity < asn_line.quantity else "asn_overage"
                )
                _add_variance(
                    receipt,
                    line,
                    variance_type,
                    "warning",
                    asn_line.quantity,
                    line.received_quantity,
                )
    if receipt.variances:
        receipt.status = "posted_with_exceptions"
    return receipt.variances


def list_receipt_variances(
    db: Session, status: str | None = None, store_number: str | None = None
) -> list[ReceiptVariance]:
    statement = (
        select(ReceiptVariance).join(PurchaseReceipt).order_by(ReceiptVariance.detected_at.desc())
    )
    if status is not None:
        statement = statement.where(ReceiptVariance.status == status)
    if store_number is not None:
        statement = statement.where(PurchaseReceipt.store_number == store_number)
    return list(db.scalars(statement).all())


def resolve_receipt_variance(
    db: Session,
    variance_id: str,
    payload: ReceiptVarianceResolution,
    actor: str,
) -> ReceiptVariance:
    variance = db.scalar(
        select(ReceiptVariance)
        .options(selectinload(ReceiptVariance.receipt).selectinload(PurchaseReceipt.variances))
        .where(ReceiptVariance.id == variance_id)
        .with_for_update()
    )
    if variance is None:
        raise ReceiptVarianceError("Receipt variance not found")
    if variance.status != "open":
        raise ReceiptVarianceError("Receipt variance is already closed")
    variance.status = "resolved" if payload.action == "resolve" else "waived"
    variance.resolution_action = payload.action
    variance.resolution_note = payload.note
    variance.resolved_by = actor
    variance.resolved_at = datetime.now(UTC)
    if all(item.status != "open" for item in variance.receipt.variances):
        variance.receipt.status = "posted"
    db.commit()
    db.refresh(variance)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type=f"receiving.variance_{variance.status}",
            entity_type="receipt_variance",
            entity_id=variance.id,
            actor=actor,
            payload={
                "receipt_id": variance.receipt_id,
                "variance_type": variance.variance_type,
                "action": payload.action,
            },
        ),
    )
    return variance
