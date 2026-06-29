import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.catalog import CatalogVendor
from app.models.event_snapshot import EventSnapshot
from app.models.purchase_order import PurchaseOrder
from app.models.vendor_integration import VendorPurchaseOrderAcknowledgement
from app.schemas.vendor_integration import (
    VendorEndpointCreate,
    VendorEndpointDirection,
    VendorEventType,
    VendorInboundEventCreate,
    VendorTransport,
)
from app.services.vendor_acknowledgement_service import process_vendor_acknowledgement
from app.services.vendor_integration_service import create_vendor_endpoint, ingest_vendor_event


def main() -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    actor = f"validation-001t2-{suffix}@example.com"
    vendor_code = f"VA-{suffix[-12:]}"
    po_number = f"PO-ACK-{suffix[-12:]}"

    with SessionLocal() as db:
        db.add(
            CatalogVendor(
                vendor_code=vendor_code,
                name="001T.2 Validation Vendor",
                is_active=True,
                source_file="001t2-validation",
            )
        )
        order = PurchaseOrder(
            po_number=po_number,
            workflow_code="BPP_PURCHASING",
            vendor_code=vendor_code,
            status="transmitted",
            currency="USD",
            subtotal=Decimal("250"),
            freight_total=Decimal("0"),
            tax_total=Decimal("0"),
            total=Decimal("250"),
            created_by=actor,
        )
        db.add(order)
        db.commit()
        endpoint = create_vendor_endpoint(
            db,
            VendorEndpointCreate(
                vendor_code=vendor_code,
                name="001T.2 acknowledgement endpoint",
                transport=VendorTransport.REST_API,
                direction=VendorEndpointDirection.INBOUND,
                connection_reference=f"vault://vendors/{vendor_code}/api",
            ),
            actor,
        )
        event, _event_created = ingest_vendor_event(
            db,
            VendorInboundEventCreate(
                endpoint_id=endpoint.id,
                external_event_id=f"ACK-{suffix}",
                event_type=VendorEventType.ACKNOWLEDGEMENT,
                payload={
                    "purchase_order_number": po_number,
                    "acknowledgement_status": "accepted_with_changes",
                    "vendor_reference": f"VREF-{suffix[-8:]}",
                    "changes": [
                        {
                            "field": "expected_ship_date",
                            "requested": None,
                            "accepted": "2026-07-15",
                        }
                    ],
                },
            ),
            actor,
        )
        acknowledgement, created = process_vendor_acknowledgement(db, event.id, actor)
        replay, replay_created = process_vendor_acknowledgement(db, event.id, actor)
        db.refresh(order)
        db.refresh(event)
        acknowledgement_count = db.scalar(
            select(func.count())
            .select_from(VendorPurchaseOrderAcknowledgement)
            .where(VendorPurchaseOrderAcknowledgement.inbound_event_id == event.id)
        )
        snapshot_count = db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(
                EventSnapshot.entity_type == "purchase_order",
                EventSnapshot.entity_id == order.id,
                EventSnapshot.event_type == "vendor.purchase_order_acknowledged",
            )
        )
        assert created is True
        assert replay_created is False
        assert replay.id == acknowledgement.id
        assert order.status == "vendor_acknowledged_changes"
        assert event.status == "processed"
        assert acknowledgement_count == 1
        assert snapshot_count == 1

        print(
            json.dumps(
                {
                    "acknowledgement_id": acknowledgement.id,
                    "acknowledgement_status": acknowledgement.acknowledgement_status,
                    "event_id": event.id,
                    "event_status": event.status,
                    "order_id": order.id,
                    "po_number": order.po_number,
                    "order_status": order.status,
                    "snapshot_count": snapshot_count,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
