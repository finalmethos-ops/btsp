from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder
from app.models.vendor_integration import (
    VendorInboundEvent,
    VendorPurchaseOrderAcknowledgement,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.vendor_integration import VendorAcknowledgementPayload
from app.services.snapshot_service import append_snapshot

ORDER_STATUS_BY_ACKNOWLEDGEMENT = {
    "accepted": "vendor_acknowledged",
    "accepted_with_changes": "vendor_acknowledged_changes",
    "rejected": "vendor_rejected",
}
ACKNOWLEDGEMENT_ELIGIBLE_ORDER_STATUSES = {
    "transmitted",
    *ORDER_STATUS_BY_ACKNOWLEDGEMENT.values(),
}


class VendorAcknowledgementError(ValueError):
    pass


def _reject_event(db: Session, event: VendorInboundEvent, message: str, actor: str) -> None:
    event.status = "rejected"
    event.error_message = message
    event.processed_at = datetime.now(UTC)
    db.commit()
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.acknowledgement_rejected",
            entity_type="vendor_inbound_event",
            entity_id=event.id,
            actor=actor,
            payload={"reason": message},
        ),
    )


def get_vendor_acknowledgement(
    db: Session, acknowledgement_id: str
) -> VendorPurchaseOrderAcknowledgement | None:
    return db.get(VendorPurchaseOrderAcknowledgement, acknowledgement_id)


def process_vendor_acknowledgement(
    db: Session, event_id: str, actor: str
) -> tuple[VendorPurchaseOrderAcknowledgement, bool]:
    event = db.scalar(
        select(VendorInboundEvent).where(VendorInboundEvent.id == event_id).with_for_update()
    )
    if event is None:
        raise VendorAcknowledgementError("Vendor inbound event not found")
    existing = db.scalar(
        select(VendorPurchaseOrderAcknowledgement).where(
            VendorPurchaseOrderAcknowledgement.inbound_event_id == event.id
        )
    )
    if existing is not None:
        return existing, False
    if event.status == "rejected":
        raise VendorAcknowledgementError(event.error_message or "Vendor event was rejected")
    if event.event_type != "acknowledgement":
        message = "Vendor event is not a purchase order acknowledgement"
        _reject_event(db, event, message, actor)
        raise VendorAcknowledgementError(message)
    try:
        payload = VendorAcknowledgementPayload.model_validate(event.payload)
    except ValidationError as exc:
        message = "Vendor acknowledgement payload is invalid"
        _reject_event(db, event, message, actor)
        raise VendorAcknowledgementError(message) from exc

    order = db.scalar(
        select(PurchaseOrder)
        .where(PurchaseOrder.po_number == payload.purchase_order_number)
        .with_for_update()
    )
    if order is None:
        message = "Purchase order referenced by acknowledgement was not found"
        _reject_event(db, event, message, actor)
        raise VendorAcknowledgementError(message)
    if order.vendor_code != event.vendor_code:
        message = "Acknowledgement vendor does not match the purchase order vendor"
        _reject_event(db, event, message, actor)
        raise VendorAcknowledgementError(message)
    if order.status not in ACKNOWLEDGEMENT_ELIGIBLE_ORDER_STATUSES:
        message = "Purchase order has not completed internal transmission"
        _reject_event(db, event, message, actor)
        raise VendorAcknowledgementError(message)

    acknowledgement = VendorPurchaseOrderAcknowledgement(
        inbound_event_id=event.id,
        endpoint_id=event.endpoint_id,
        purchase_order_id=order.id,
        vendor_code=event.vendor_code,
        acknowledgement_status=payload.acknowledgement_status.value,
        vendor_reference=payload.vendor_reference,
        acknowledged_at=payload.acknowledged_at or event.occurred_at,
        expected_ship_date=payload.expected_ship_date,
        reason=payload.reason,
        changes=payload.changes,
        created_by=actor,
    )
    event.status = "processed"
    event.processed_at = datetime.now(UTC)
    event.error_message = None
    order.status = ORDER_STATUS_BY_ACKNOWLEDGEMENT[payload.acknowledgement_status.value]
    db.add(acknowledgement)
    db.commit()
    db.refresh(acknowledgement)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.purchase_order_acknowledged",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={
                "acknowledgement_id": acknowledgement.id,
                "inbound_event_id": event.id,
                "vendor_code": event.vendor_code,
                "acknowledgement_status": acknowledgement.acknowledgement_status,
                "vendor_reference": acknowledgement.vendor_reference,
                "changes": acknowledgement.changes,
            },
        ),
    )
    return acknowledgement, True


def list_vendor_acknowledgements(
    db: Session,
    purchase_order_id: str | None = None,
    vendor_code: str | None = None,
    acknowledgement_status: str | None = None,
) -> list[VendorPurchaseOrderAcknowledgement]:
    statement = select(VendorPurchaseOrderAcknowledgement).order_by(
        VendorPurchaseOrderAcknowledgement.created_at.desc()
    )
    if purchase_order_id is not None:
        statement = statement.where(
            VendorPurchaseOrderAcknowledgement.purchase_order_id == purchase_order_id
        )
    if vendor_code is not None:
        statement = statement.where(VendorPurchaseOrderAcknowledgement.vendor_code == vendor_code)
    if acknowledgement_status is not None:
        statement = statement.where(
            VendorPurchaseOrderAcknowledgement.acknowledgement_status == acknowledgement_status
        )
    return list(db.scalars(statement).all())
