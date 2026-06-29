import json
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.event_snapshot import EventSnapshot
from app.models.identity import User
from app.models.purchase_order import PurchaseOrderTransmissionEvent
from app.models.store import Store
from app.schemas.flow import FlowActionRequest
from app.schemas.purchase_order_artifact import PurchaseOrderArtifactFormat
from app.schemas.purchase_order_transmission import (
    PurchaseOrderTransmissionAction,
    PurchaseOrderTransmissionChannel,
)
from app.schemas.purchasing import PurchaseLineWrite, PurchaseRequestCreate
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.catalog_import_service import import_catalog
from app.services.purchase_order_artifact_service import artifact_path, generate_artifact
from app.services.purchase_order_service import (
    generate_purchase_orders,
    seed_purchase_order_defaults,
)
from app.services.purchase_order_transmission_service import (
    apply_transmission_action,
    create_transmission,
)
from app.services.purchase_request_service import (
    add_line_item,
    create_purchase_request,
    submit_purchase_request,
)
from app.services.workflow_engine import advance_workflow


def _catalog(vendor_code: str, product_code: str) -> bytes:
    workbook = Workbook()
    vendors = workbook.active
    vendors.title = "Vendors"
    vendors.append(["vendor_code", "name", "is_active"])
    vendors.append([vendor_code, "001S Validation Vendor", True])
    products = workbook.create_sheet("Products")
    products.append(
        [
            "product_code",
            "vendor_code",
            "name",
            "unit_price",
            "currency",
            "minimum_order_quantity",
            "is_available",
            "is_active",
        ]
    )
    products.append(
        [product_code, vendor_code, "001S Validation Product", 125, "USD", 1, True, True]
    )
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def main() -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    actor = f"validation-001s-{suffix}@example.com"
    store_number = f"V{suffix[-12:]}"
    vendor_code = f"V-{suffix[-12:]}"
    product_code = f"P-{suffix[-12:]}"

    with SessionLocal() as db:
        seed_bpp_purchasing(db, actor)
        seed_purchase_order_defaults(db, actor)
        db.add(
            Store(
                store_number=store_number,
                name="001S Validation Store",
                region_code="VALIDATION",
                is_active=True,
                is_ordering_enabled=True,
            )
        )
        user = User(
            email=actor,
            display_name="001S Validator",
            password_hash="validation-only",
            region_code="VALIDATION",
            is_active=True,
        )
        db.add(user)
        db.commit()

        import_catalog(db, f"001s-{suffix}.xlsx", _catalog(vendor_code, product_code), actor)
        request = create_purchase_request(
            db,
            PurchaseRequestCreate(
                workflow_code="BPP_PURCHASING",
                store_number=store_number,
                vendor_code=vendor_code,
            ),
            actor,
        )
        add_line_item(
            db,
            request,
            PurchaseLineWrite(product_code=product_code, quantity=2),
            actor,
        )
        submit_purchase_request(db, request, user, {"workflow.bpp.submit"})
        for action, permission in (
            ("submit_for_department_review", "workflow.bpp.submit"),
            ("department_approve", "workflow.bpp.department_review"),
            ("purchasing_approve", "workflow.bpp.purchasing_review"),
            ("select_vendor", "workflow.bpp.vendor_select"),
            ("verify_cost", "workflow.bpp.cost_verify"),
            ("executive_approve", "workflow.bpp.executive_approve"),
        ):
            advance_workflow(
                db,
                request.workflow_instance_id,
                FlowActionRequest(action=action, actor=actor),
                {permission},
            )

        order = generate_purchase_orders(
            db,
            [request.id],
            actor,
            {"workflow.bpp.po_generate"},
        )[0]
        artifacts = [
            generate_artifact(
                db, order, artifact_format, actor, settings.purchase_order_export_path
            )
            for artifact_format in PurchaseOrderArtifactFormat
        ]
        advance_workflow(
            db,
            request.workflow_instance_id,
            FlowActionRequest(action="generate_po", actor=actor),
            {"workflow.bpp.po_generate"},
        )
        transmission = create_transmission(
            db,
            order,
            artifacts[0].id,
            PurchaseOrderTransmissionChannel.MANUAL,
            "001S production validation",
            "Operator-controlled validation handoff",
            actor,
            {"workflow.bpp.vendor_submit"},
        )
        for action in (
            PurchaseOrderTransmissionAction.RELEASE,
            PurchaseOrderTransmissionAction.MARK_DELIVERED,
        ):
            transmission = apply_transmission_action(
                db,
                order,
                transmission,
                action,
                "001S production validation",
                actor,
                {"workflow.bpp.vendor_submit"},
            )

        db.refresh(order)
        db.refresh(transmission)
        snapshot_count = db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(EventSnapshot.entity_id == order.id)
        )
        event_count = db.scalar(
            select(func.count())
            .select_from(PurchaseOrderTransmissionEvent)
            .where(PurchaseOrderTransmissionEvent.transmission_id == transmission.id)
        )
        assert order.status == "transmitted"
        assert transmission.status == "delivered"
        assert snapshot_count == 7
        assert event_count == 3
        assert all(
            artifact_path(item, settings.purchase_order_export_path).is_file() for item in artifacts
        )
        assert Path(settings.purchase_order_export_path).is_dir()

        print(
            json.dumps(
                {
                    "actor": actor,
                    "request_id": request.id,
                    "order_id": order.id,
                    "po_number": order.po_number,
                    "order_status": order.status,
                    "transmission_id": transmission.id,
                    "transmission_status": transmission.status,
                    "transmission_events": event_count,
                    "snapshots": snapshot_count,
                    "artifacts": [
                        {
                            "format": item.artifact_format,
                            "filename": item.stored_filename,
                            "sha256": item.sha256,
                            "size_bytes": item.size_bytes,
                        }
                        for item in artifacts
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
