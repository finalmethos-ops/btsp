from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderArtifact,
    PurchaseOrderSource,
    PurchaseOrderTransmission,
    PurchaseOrderTransmissionEvent,
)
from app.models.purchasing import PurchaseRequest
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.purchase_order_transmission import (
    PurchaseOrderTransmissionAction,
    PurchaseOrderTransmissionChannel,
)
from app.services.snapshot_service import append_snapshot

TRANSITIONS = {
    ("prepared", PurchaseOrderTransmissionAction.RELEASE): "ready",
    ("ready", PurchaseOrderTransmissionAction.MARK_DELIVERED): "delivered",
    ("ready", PurchaseOrderTransmissionAction.MARK_FAILED): "failed",
    ("prepared", PurchaseOrderTransmissionAction.CANCEL): "cancelled",
    ("ready", PurchaseOrderTransmissionAction.CANCEL): "cancelled",
    ("failed", PurchaseOrderTransmissionAction.CANCEL): "cancelled",
    ("failed", PurchaseOrderTransmissionAction.RETRY): "prepared",
}

ORDER_STATUS_BY_TRANSMISSION = {
    "prepared": "transmission_prepared",
    "ready": "transmission_ready",
    "delivered": "transmitted",
    "failed": "transmission_failed",
    "cancelled": "transmission_cancelled",
}


class PurchaseOrderTransmissionError(ValueError):
    pass


def _required_permission(workflow_code: str) -> str:
    if workflow_code == "BPP_PURCHASING":
        return "workflow.bpp.vendor_submit"
    if workflow_code == "IND_PURCHASING":
        return "workflow.ind.review"
    raise PurchaseOrderTransmissionError("Unsupported Purchase Order workflow")


def _require_permission(order: PurchaseOrder, permission_codes: set[str]) -> None:
    required = _required_permission(order.workflow_code)
    if required not in permission_codes:
        raise PermissionError(required)


def _validate_source_state(db: Session, order_id: str) -> None:
    source_ids = list(
        db.scalars(
            select(PurchaseOrderSource.purchase_request_id).where(
                PurchaseOrderSource.purchase_order_id == order_id
            )
        ).all()
    )
    states = dict(
        db.execute(
            select(PurchaseRequest.id, PurchaseRequest.status).where(
                PurchaseRequest.id.in_(source_ids)
            )
        ).all()
    )
    if not source_ids or any(
        states.get(source_id) != "vendor_submission" for source_id in source_ids
    ):
        raise PurchaseOrderTransmissionError(
            "All source requests must be in vendor_submission before transmission"
        )


def create_transmission(
    db: Session,
    order: PurchaseOrder,
    artifact_id: str,
    channel: PurchaseOrderTransmissionChannel,
    destination: str | None,
    notes: str | None,
    actor: str,
    permission_codes: set[str],
) -> PurchaseOrderTransmission:
    _require_permission(order, permission_codes)
    _validate_source_state(db, order.id)
    artifact = db.scalar(
        select(PurchaseOrderArtifact).where(
            PurchaseOrderArtifact.id == artifact_id,
            PurchaseOrderArtifact.purchase_order_id == order.id,
        )
    )
    if artifact is None:
        raise PurchaseOrderTransmissionError("Purchase Order artifact not found")
    existing = db.scalar(
        select(PurchaseOrderTransmission).where(
            PurchaseOrderTransmission.artifact_id == artifact_id
        )
    )
    if existing is not None:
        raise PurchaseOrderTransmissionError("A transmission already exists for this artifact")
    transmission = PurchaseOrderTransmission(
        purchase_order_id=order.id,
        artifact_id=artifact.id,
        channel=channel.value,
        destination=destination,
        status="prepared",
        notes=notes,
        created_by=actor,
        updated_by=actor,
    )
    transmission.events.append(
        PurchaseOrderTransmissionEvent(
            event_type="prepared",
            from_status=None,
            to_status="prepared",
            actor=actor,
        )
    )
    order.status = ORDER_STATUS_BY_TRANSMISSION["prepared"]
    db.add(transmission)
    db.commit()
    db.refresh(transmission)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_order.transmission_created",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={
                "transmission_id": transmission.id,
                "artifact_id": artifact.id,
                "channel": transmission.channel,
                "status": transmission.status,
            },
        ),
    )
    return transmission


def apply_transmission_action(
    db: Session,
    order: PurchaseOrder,
    transmission: PurchaseOrderTransmission,
    action: PurchaseOrderTransmissionAction,
    reason: str | None,
    actor: str,
    permission_codes: set[str],
) -> PurchaseOrderTransmission:
    _require_permission(order, permission_codes)
    target = TRANSITIONS.get((transmission.status, action))
    if target is None:
        raise PurchaseOrderTransmissionError("Transmission action is not valid for current status")
    if action is PurchaseOrderTransmissionAction.MARK_FAILED and not reason:
        raise PurchaseOrderTransmissionError("Failure reason is required")
    previous = transmission.status
    transmission.status = target
    transmission.updated_by = actor
    transmission.events.append(
        PurchaseOrderTransmissionEvent(
            event_type=action.value,
            from_status=previous,
            to_status=target,
            reason=reason,
            actor=actor,
        )
    )
    order.status = ORDER_STATUS_BY_TRANSMISSION[target]
    db.commit()
    db.refresh(transmission)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_order.transmission_status_changed",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={
                "transmission_id": transmission.id,
                "action": action.value,
                "from_status": previous,
                "to_status": target,
                "reason": reason,
            },
        ),
    )
    return transmission


def list_transmissions(db: Session, order_id: str) -> list[PurchaseOrderTransmission]:
    return list(
        db.scalars(
            select(PurchaseOrderTransmission)
            .options(selectinload(PurchaseOrderTransmission.events))
            .where(PurchaseOrderTransmission.purchase_order_id == order_id)
            .order_by(PurchaseOrderTransmission.created_at)
        )
        .unique()
        .all()
    )


def get_transmission(
    db: Session, order_id: str, transmission_id: str
) -> PurchaseOrderTransmission | None:
    return db.scalar(
        select(PurchaseOrderTransmission)
        .options(selectinload(PurchaseOrderTransmission.events))
        .where(
            PurchaseOrderTransmission.id == transmission_id,
            PurchaseOrderTransmission.purchase_order_id == order_id,
        )
    )
