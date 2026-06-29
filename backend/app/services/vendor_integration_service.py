import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import CatalogVendor
from app.models.vendor_integration import VendorEndpoint, VendorInboundEvent
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.vendor_integration import VendorEndpointCreate, VendorInboundEventCreate
from app.services.snapshot_service import append_snapshot


class VendorIntegrationError(ValueError):
    pass


def _payload_hash(payload: dict[str, object]) -> str:
    try:
        canonical = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VendorIntegrationError("Vendor event payload must be valid JSON") from exc
    return hashlib.sha256(canonical).hexdigest()


def create_vendor_endpoint(
    db: Session, payload: VendorEndpointCreate, actor: str
) -> VendorEndpoint:
    vendor = db.scalar(
        select(CatalogVendor).where(CatalogVendor.vendor_code == payload.vendor_code)
    )
    if vendor is None or not vendor.is_active:
        raise VendorIntegrationError("Vendor is not active in the internal catalog")
    endpoint = VendorEndpoint(
        **payload.model_dump(mode="json"),
        created_by=actor,
        updated_by=actor,
    )
    db.add(endpoint)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise VendorIntegrationError("A vendor endpoint with this name already exists") from exc
    db.refresh(endpoint)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.endpoint_created",
            entity_type="vendor_endpoint",
            entity_id=endpoint.id,
            actor=actor,
            payload={
                "vendor_code": endpoint.vendor_code,
                "transport": endpoint.transport,
                "direction": endpoint.direction,
            },
        ),
    )
    return endpoint


def list_vendor_endpoints(
    db: Session, vendor_code: str | None = None, active_only: bool = True
) -> list[VendorEndpoint]:
    statement = select(VendorEndpoint).order_by(VendorEndpoint.vendor_code, VendorEndpoint.name)
    if vendor_code is not None:
        statement = statement.where(VendorEndpoint.vendor_code == vendor_code)
    if active_only:
        statement = statement.where(VendorEndpoint.is_active.is_(True))
    return list(db.scalars(statement).all())


def get_vendor_endpoint(db: Session, endpoint_id: str) -> VendorEndpoint | None:
    return db.get(VendorEndpoint, endpoint_id)


def _same_event(
    existing: VendorInboundEvent, payload: VendorInboundEventCreate, digest: str
) -> bool:
    return (
        existing.event_type == payload.event_type.value
        and existing.payload_sha256 == digest
        and existing.occurred_at == payload.occurred_at
    )


def ingest_vendor_event(
    db: Session,
    payload: VendorInboundEventCreate,
    actor: str,
    import_run_id: str | None = None,
) -> tuple[VendorInboundEvent, bool]:
    endpoint = get_vendor_endpoint(db, payload.endpoint_id)
    if endpoint is None or not endpoint.is_active:
        raise VendorIntegrationError("Vendor endpoint is not active")
    if endpoint.direction not in {"inbound", "bidirectional"}:
        raise VendorIntegrationError("Vendor endpoint does not accept inbound events")
    digest = _payload_hash(payload.payload)
    existing = db.scalar(
        select(VendorInboundEvent).where(
            VendorInboundEvent.endpoint_id == endpoint.id,
            VendorInboundEvent.external_event_id == payload.external_event_id,
        )
    )
    if existing is not None:
        if not _same_event(existing, payload, digest):
            raise VendorIntegrationError(
                "External event ID was already used with different event content"
            )
        return existing, False

    event = VendorInboundEvent(
        endpoint_id=endpoint.id,
        import_run_id=import_run_id,
        vendor_code=endpoint.vendor_code,
        external_event_id=payload.external_event_id,
        event_type=payload.event_type.value,
        payload=payload.payload,
        payload_sha256=digest,
        status="received",
        occurred_at=payload.occurred_at,
        received_by=actor,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(VendorInboundEvent).where(
                VendorInboundEvent.endpoint_id == endpoint.id,
                VendorInboundEvent.external_event_id == payload.external_event_id,
            )
        )
        if existing is None or not _same_event(existing, payload, digest):
            raise VendorIntegrationError(
                "External event ID was already used with different event content"
            ) from exc
        return existing, False
    db.refresh(event)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.inbound_event_received",
            entity_type="vendor_inbound_event",
            entity_id=event.id,
            actor=actor,
            payload={
                "endpoint_id": endpoint.id,
                "vendor_code": endpoint.vendor_code,
                "external_event_id": event.external_event_id,
                "event_type": event.event_type,
                "payload_sha256": event.payload_sha256,
            },
        ),
    )
    return event, True


def list_vendor_events(
    db: Session,
    endpoint_id: str | None = None,
    vendor_code: str | None = None,
    event_type: str | None = None,
) -> list[VendorInboundEvent]:
    statement = select(VendorInboundEvent).order_by(VendorInboundEvent.received_at.desc())
    if endpoint_id is not None:
        statement = statement.where(VendorInboundEvent.endpoint_id == endpoint_id)
    if vendor_code is not None:
        statement = statement.where(VendorInboundEvent.vendor_code == vendor_code)
    if event_type is not None:
        statement = statement.where(VendorInboundEvent.event_type == event_type)
    return list(db.scalars(statement).all())
