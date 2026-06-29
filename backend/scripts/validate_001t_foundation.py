import json
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.catalog import CatalogVendor
from app.models.event_snapshot import EventSnapshot
from app.models.vendor_integration import VendorInboundEvent
from app.schemas.vendor_integration import (
    VendorEndpointCreate,
    VendorEndpointDirection,
    VendorEventType,
    VendorInboundEventCreate,
    VendorTransport,
)
from app.services.vendor_integration_service import create_vendor_endpoint, ingest_vendor_event


def main() -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    actor = f"validation-001t-{suffix}@example.com"
    vendor_code = f"VT-{suffix[-12:]}"

    with SessionLocal() as db:
        db.add(
            CatalogVendor(
                vendor_code=vendor_code,
                name="001T Validation Vendor",
                is_active=True,
                source_file="001t-validation",
            )
        )
        db.commit()
        endpoint = create_vendor_endpoint(
            db,
            VendorEndpointCreate(
                vendor_code=vendor_code,
                name="001T validation inbound",
                transport=VendorTransport.REST_API,
                direction=VendorEndpointDirection.INBOUND,
                connection_reference=f"vault://vendors/{vendor_code}/api",
                configuration={"base_url": "https://vendor.validation.invalid"},
            ),
            actor,
        )
        payload = VendorInboundEventCreate(
            endpoint_id=endpoint.id,
            external_event_id=f"ACK-{suffix}",
            event_type=VendorEventType.ACKNOWLEDGEMENT,
            payload={"purchase_order": "PO-2026-000005", "accepted": True},
        )
        event, created = ingest_vendor_event(db, payload, actor)
        replay, replay_created = ingest_vendor_event(db, payload, actor)
        snapshot_count = db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(EventSnapshot.entity_id.in_([endpoint.id, event.id]))
        )
        event_count = db.scalar(
            select(func.count())
            .select_from(VendorInboundEvent)
            .where(VendorInboundEvent.endpoint_id == endpoint.id)
        )
        assert created is True
        assert replay_created is False
        assert replay.id == event.id
        assert event_count == 1
        assert snapshot_count == 2

        print(
            json.dumps(
                {
                    "actor": actor,
                    "endpoint_id": endpoint.id,
                    "event_id": event.id,
                    "external_event_id": event.external_event_id,
                    "payload_sha256": event.payload_sha256,
                    "status": event.status,
                    "event_count": event_count,
                    "snapshot_count": snapshot_count,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
