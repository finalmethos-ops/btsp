from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.vendor_integration import (
    VendorAdvanceShipNotice,
    VendorAdvanceShipNoticeLine,
    VendorInboundEvent,
    VendorShipment,
    VendorShipmentUpdate,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.vendor_integration import VendorASNPayload, VendorShipmentUpdatePayload
from app.services.snapshot_service import append_snapshot

SHIPMENT_TRANSITIONS = {
    "planned": {"in_transit", "delayed", "cancelled"},
    "in_transit": {"delayed", "delivered"},
    "delayed": {"in_transit", "cancelled"},
}
PO_STATUS_BY_SHIPMENT = {
    "planned": "shipment_planned",
    "in_transit": "shipment_in_transit",
    "delayed": "shipment_delayed",
    "delivered": "shipment_delivered",
    "cancelled": "shipment_cancelled",
}
SHIPMENT_ELIGIBLE_PO_STATUSES = {
    "vendor_acknowledged",
    "vendor_acknowledged_changes",
    *PO_STATUS_BY_SHIPMENT.values(),
}


class VendorShipmentError(ValueError):
    pass


def _event(db: Session, event_id: str, expected_type: str) -> VendorInboundEvent:
    event = db.scalar(
        select(VendorInboundEvent).where(VendorInboundEvent.id == event_id).with_for_update()
    )
    if event is None:
        raise VendorShipmentError("Vendor inbound event not found")
    if event.status == "rejected":
        raise VendorShipmentError(event.error_message or "Vendor event was rejected")
    if event.event_type != expected_type:
        raise VendorShipmentError(f"Vendor event is not a {expected_type.replace('_', ' ')}")
    return event


def _reject(db: Session, event: VendorInboundEvent, message: str, actor: str) -> None:
    event.status = "rejected"
    event.error_message = message
    event.processed_at = datetime.now(UTC)
    db.commit()
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.logistics_event_rejected",
            entity_type="vendor_inbound_event",
            entity_id=event.id,
            actor=actor,
            payload={"reason": message},
        ),
    )


def _order(db: Session, po_number: str, vendor_code: str) -> PurchaseOrder:
    order = db.scalar(
        select(PurchaseOrder).where(PurchaseOrder.po_number == po_number).with_for_update()
    )
    if order is None:
        raise VendorShipmentError("Purchase order was not found")
    if order.vendor_code != vendor_code:
        raise VendorShipmentError("Logistics event vendor does not match purchase order vendor")
    if order.status not in SHIPMENT_ELIGIBLE_PO_STATUSES:
        raise VendorShipmentError("Purchase order is not eligible for vendor logistics")
    return order


def process_shipment_update(
    db: Session, event_id: str, actor: str
) -> tuple[VendorShipmentUpdate, bool]:
    existing = db.scalar(
        select(VendorShipmentUpdate).where(VendorShipmentUpdate.inbound_event_id == event_id)
    )
    if existing is not None:
        return existing, False
    event = _event(db, event_id, "shipment_update")
    try:
        payload = VendorShipmentUpdatePayload.model_validate(event.payload)
        order = _order(db, payload.purchase_order_number, event.vendor_code)
    except (ValidationError, VendorShipmentError) as exc:
        message = "Vendor shipment update is invalid"
        _reject(db, event, message, actor)
        raise VendorShipmentError(message) from exc
    shipment = db.scalar(
        select(VendorShipment)
        .where(
            VendorShipment.vendor_code == event.vendor_code,
            VendorShipment.shipment_number == payload.shipment_number,
        )
        .with_for_update()
    )
    if shipment is None:
        if payload.status.value not in {"planned", "in_transit", "delayed"}:
            _reject(db, event, "Initial shipment status is invalid", actor)
            raise VendorShipmentError("Initial shipment status is invalid")
        shipment = VendorShipment(
            purchase_order_id=order.id,
            vendor_code=event.vendor_code,
            shipment_number=payload.shipment_number,
            status=payload.status.value,
        )
        db.add(shipment)
        db.flush()
    elif shipment.purchase_order_id != order.id:
        _reject(db, event, "Shipment belongs to a different purchase order", actor)
        raise VendorShipmentError("Shipment belongs to a different purchase order")
    elif (
        payload.status.value != shipment.status
        and payload.status.value not in SHIPMENT_TRANSITIONS.get(shipment.status, set())
    ):
        _reject(db, event, "Shipment status transition is invalid", actor)
        raise VendorShipmentError("Shipment status transition is invalid")
    shipment.status = payload.status.value
    shipment.carrier = payload.carrier or shipment.carrier
    shipment.tracking_number = payload.tracking_number or shipment.tracking_number
    shipment.estimated_delivery_at = payload.estimated_delivery_at or shipment.estimated_delivery_at
    shipment.shipped_at = payload.shipped_at or shipment.shipped_at
    shipment.delivered_at = payload.delivered_at or shipment.delivered_at
    update = VendorShipmentUpdate(
        inbound_event_id=event.id,
        shipment_id=shipment.id,
        status=payload.status.value,
        occurred_at=event.occurred_at,
        location=payload.location,
        notes=payload.notes,
        created_by=actor,
    )
    event.status = "processed"
    event.processed_at = datetime.now(UTC)
    order.status = PO_STATUS_BY_SHIPMENT[payload.status.value]
    db.add(update)
    db.commit()
    db.refresh(update)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.shipment_updated",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={"shipment_id": shipment.id, "status": shipment.status},
        ),
    )
    return update, True


def process_asn(db: Session, event_id: str, actor: str) -> tuple[VendorAdvanceShipNotice, bool]:
    existing = db.scalar(
        select(VendorAdvanceShipNotice)
        .options(selectinload(VendorAdvanceShipNotice.lines))
        .where(VendorAdvanceShipNotice.inbound_event_id == event_id)
    )
    if existing is not None:
        return existing, False
    event = _event(db, event_id, "asn")
    try:
        payload = VendorASNPayload.model_validate(event.payload)
        order = _order(db, payload.purchase_order_number, event.vendor_code)
    except (ValidationError, VendorShipmentError) as exc:
        message = "Vendor ASN is invalid"
        _reject(db, event, message, actor)
        raise VendorShipmentError(message) from exc
    shipment = None
    if payload.shipment_number:
        shipment = db.scalar(
            select(VendorShipment).where(
                VendorShipment.vendor_code == event.vendor_code,
                VendorShipment.shipment_number == payload.shipment_number,
            )
        )
        if shipment is not None and shipment.purchase_order_id != order.id:
            _reject(db, event, "ASN shipment belongs to a different purchase order", actor)
            raise VendorShipmentError("ASN shipment belongs to a different purchase order")
    order_lines = {
        line.id: line
        for line in db.scalars(
            select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == order.id)
        ).all()
    }
    asn = VendorAdvanceShipNotice(
        inbound_event_id=event.id,
        purchase_order_id=order.id,
        shipment_id=shipment.id if shipment else None,
        vendor_code=event.vendor_code,
        asn_number=payload.asn_number,
        expected_delivery_at=payload.expected_delivery_at,
        status="received",
        created_by=actor,
    )
    for requested in payload.lines:
        line = order_lines.get(requested.purchase_order_line_id)
        quantity = Decimal(str(requested.quantity))
        if line is None or line.product_code != requested.product_code:
            _reject(db, event, "ASN line does not match a purchase order line", actor)
            raise VendorShipmentError("ASN line does not match a purchase order line")
        advised = db.scalar(
            select(func.coalesce(func.sum(VendorAdvanceShipNoticeLine.quantity), 0)).where(
                VendorAdvanceShipNoticeLine.purchase_order_line_id == line.id
            )
        )
        if Decimal(str(advised)) + quantity > line.quantity:
            _reject(db, event, "ASN cumulative quantity exceeds ordered quantity", actor)
            raise VendorShipmentError("ASN cumulative quantity exceeds ordered quantity")
        asn.lines.append(
            VendorAdvanceShipNoticeLine(
                purchase_order_line_id=line.id,
                product_code=line.product_code,
                quantity=quantity,
                lot_number=requested.lot_number,
            )
        )
    event.status = "processed"
    event.processed_at = datetime.now(UTC)
    db.add(asn)
    db.commit()
    db.refresh(asn)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.asn_received",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={"asn_id": asn.id, "asn_number": asn.asn_number, "line_count": len(asn.lines)},
        ),
    )
    return asn, True


def list_shipments(db: Session, purchase_order_id: str | None = None) -> list[VendorShipment]:
    statement = select(VendorShipment).order_by(VendorShipment.updated_at.desc())
    if purchase_order_id:
        statement = statement.where(VendorShipment.purchase_order_id == purchase_order_id)
    return list(db.scalars(statement).all())


def list_asns(db: Session, purchase_order_id: str | None = None) -> list[VendorAdvanceShipNotice]:
    statement = (
        select(VendorAdvanceShipNotice)
        .options(selectinload(VendorAdvanceShipNotice.lines))
        .order_by(VendorAdvanceShipNotice.created_at.desc())
    )
    if purchase_order_id:
        statement = statement.where(VendorAdvanceShipNotice.purchase_order_id == purchase_order_id)
    return list(db.scalars(statement).unique().all())
