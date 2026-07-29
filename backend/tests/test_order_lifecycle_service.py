from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogProduct, CatalogVendor, VendorMOQRule
from app.models.configuration import ConfigurationEntry  # noqa: F401
from app.models.event_snapshot import EventSnapshot  # noqa: F401
from app.models.store import Store
from app.schemas.order_lifecycle import LifecycleLineWrite
from app.services.order_lifecycle_service import (
    OrderLifecycleError,
    complete_reconciliation,
    create_purchasing_po_change,
    create_vendor_po_issue,
    create_vendor_request,
    create_vendor_requests,
    decide_request,
    delete_vendor_request,
    list_purchasing_pos,
    list_purchasing_requests,
    list_substitute_options,
    list_vendor_pos,
    receive_po_line,
    remove_model_for_vendor_attention,
    respond_to_attention,
    respond_to_po,
    submit_vendor_request,
    update_active_po_eta,
    write_request_line,
)
from app.services.purchase_order_service import (
    handoff_purchase_order,
    seed_purchase_order_defaults,
)


def test_vendor_request_to_reconciled_po_lifecycle() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                CatalogVendor(
                    vendor_code="V-LIFE",
                    name="Lifecycle Vendor",
                    is_active=True,
                    source_file="test.xlsx",
                ),
                Store(
                    store_number="100",
                    name="Lifecycle Store",
                    region_code="EAST",
                    state_code="FL",
                    is_active=True,
                    is_ordering_enabled=True,
                ),
            ]
        )
        db.flush()
        moq_rule = VendorMOQRule(
            vendor_code="V-LIFE",
            code="STANDARD",
            name="Standard MOQ",
            threshold_type="unit_quantity",
            threshold_value=2,
            is_active=True,
        )
        db.add(moq_rule)
        db.flush()
        db.add(
            CatalogProduct(
                product_code="LIFE-1",
                vendor_code="V-LIFE",
                name="Lifecycle Model",
                unit_price=Decimal("250.00"),
                currency="USD",
                minimum_order_quantity=1,
                moq_rule_id=moq_rule.id,
                is_available=True,
                is_active=True,
                source_file="test.xlsx",
            )
        )
        db.add_all(
            [
                CatalogProduct(
                    product_code="LIFE-HIGH",
                    vendor_code="V-LIFE",
                    name="Higher Cost Substitute",
                    unit_price=Decimal("300.00"),
                    currency="USD",
                    minimum_order_quantity=1,
                    moq_rule_id=moq_rule.id,
                    is_available=True,
                    is_active=True,
                    source_file="test.xlsx",
                ),
                CatalogProduct(
                    product_code="LIFE-LOW",
                    vendor_code="V-LIFE",
                    name="Lower Cost Model",
                    unit_price=Decimal("200.00"),
                    currency="USD",
                    minimum_order_quantity=1,
                    moq_rule_id=moq_rule.id,
                    is_available=True,
                    is_active=True,
                    source_file="test.xlsx",
                ),
                CatalogProduct(
                    product_code="LIFE-OTHER-MOQ",
                    vendor_code="V-LIFE",
                    name="Other MOQ Model",
                    unit_price=Decimal("400.00"),
                    currency="USD",
                    minimum_order_quantity=1,
                    moq_rule_id=None,
                    is_available=True,
                    is_active=True,
                    source_file="test.xlsx",
                ),
            ]
        )
        db.commit()
        seed_purchase_order_defaults(db, "admin@example.com")

        request = create_vendor_request(
            db,
            "V-LIFE",
            "100",
            "vendor@example.com",
            date(2026, 8, 1),
        )
        request = write_request_line(
            db,
            request,
            LifecycleLineWrite(
                product_code="LIFE-1",
                quantity=2,
            ),
            "vendor@example.com",
        )
        submit_vendor_request(db, request, "vendor@example.com")
        assert list_purchasing_requests(db)[0].id == request.id

        request = write_request_line(
            db,
            request,
            LifecycleLineWrite(product_code="LIFE-1", quantity=1),
            "buyer@example.com",
            request.line_items[0].id,
        )
        with pytest.raises(OrderLifecycleError, match="approval blocked by vendor MOQ"):
            decide_request(
                db,
                request,
                "approve",
                None,
                "buyer@example.com",
                date(2026, 8, 3),
            )
        request = write_request_line(
            db,
            request,
            LifecycleLineWrite(product_code="LIFE-1", quantity=3),
            "buyer@example.com",
            request.line_items[0].id,
        )

        order = decide_request(
            db,
            request,
            "approve",
            None,
            "buyer@example.com",
            date(2026, 8, 3),
        )
        assert order is not None
        assert order.status == "awaiting_vendor_acceptance"
        assert order.expected_delivery_date == date(2026, 8, 3)
        assert [
            model.product_code for model in list_substitute_options(db, order, order.lines[0].id)
        ] == ["LIFE-HIGH"]
        with pytest.raises(OrderLifecycleError, match="no longer editable"):
            write_request_line(
                db,
                request,
                LifecycleLineWrite(
                    product_code="LIFE-1",
                    quantity=3,
                ),
                "vendor@example.com",
            )

        assert list_vendor_pos(db, "V-LIFE", "pending")[0].id == order.id
        assert (
            list_vendor_pos(
                db,
                "V-LIFE",
                "pending",
                search=order.po_number[3:9],
                region_code="EAST",
                store_number="100",
                date_from=date(2020, 1, 1),
            )[0].id
            == order.id
        )
        assert not list_vendor_pos(db, "V-LIFE", "pending", store_number="DOES-NOT-EXIST")
        with pytest.raises(OrderLifecycleError, match="cannot be earlier"):
            respond_to_po(
                db,
                order,
                "accept",
                date(2026, 8, 2),
                None,
                "vendor@example.com",
            )
        respond_to_po(
            db,
            order,
            "accept",
            date(2026, 8, 5),
            None,
            "vendor@example.com",
        )
        update_active_po_eta(db, order, date(2026, 8, 6), "vendor@example.com")
        order = create_vendor_po_issue(
            db,
            order,
            "backorder",
            order.lines[0].id,
            Decimal("1"),
            date(2026, 8, 8),
            None,
            "Factory delay",
            "vendor@example.com",
        )
        assert order.status == "purchasing_attention"
        order = respond_to_attention(
            db,
            order,
            order.attention_items[0].id,
            "acknowledge",
            "purchasing",
            "buyer@example.com",
        )
        assert order.status == "vendor_attention"
        confirmation = next(
            item
            for item in order.attention_items
            if item.status == "pending" and item.action_type == "vendor_change_confirmation"
        )
        order = respond_to_attention(
            db,
            order,
            confirmation.id,
            "confirm",
            "vendor",
            "vendor@example.com",
            note="Confirmed",
        )
        assert order.status == "active"
        proof_events = list(
            db.scalars(
                select(EventSnapshot).where(
                    EventSnapshot.entity_id == order.id,
                    EventSnapshot.event_type.in_(
                        {
                            "purchase_order.vendor_change_approved",
                            "purchase_order.vendor_change_confirmed",
                        }
                    ),
                )
            ).all()
        )
        assert {event.event_type for event in proof_events} == {
            "purchase_order.vendor_change_approved",
            "purchase_order.vendor_change_confirmed",
        }
        assert (
            next(
                event
                for event in proof_events
                if event.event_type == "purchase_order.vendor_change_confirmed"
            ).actor
            == "vendor@example.com"
        )

        original_line = next(line for line in order.lines if line.product_code == "LIFE-1")
        order = create_vendor_po_issue(
            db,
            order,
            "out_of_stock",
            original_line.id,
            Decimal("2"),
            None,
            "LIFE-HIGH",
            "Use the proposed substitute",
            "vendor@example.com",
        )
        stock_issue = next(
            item
            for item in order.attention_items
            if item.status == "pending" and item.action_type == "out_of_stock"
        )
        order = respond_to_attention(
            db,
            order,
            stock_issue.id,
            "acknowledge",
            "purchasing",
            "buyer@example.com",
        )
        assert order.status == "vendor_attention"
        assert next(line for line in order.lines if line.product_code == "LIFE-1").quantity == 1
        assert next(line for line in order.lines if line.product_code == "LIFE-HIGH").quantity == 2
        substitution_confirmation = next(
            item
            for item in order.attention_items
            if item.status == "pending" and item.action_type == "vendor_change_confirmation"
        )
        assert substitution_confirmation.payload["resolution_action"] == "approved_substitution"
        order = respond_to_attention(
            db,
            order,
            substitution_confirmation.id,
            "confirm",
            "vendor",
            "vendor@example.com",
        )
        assert order.status == "active"

        remaining_original = next(line for line in order.lines if line.product_code == "LIFE-1")
        order = create_vendor_po_issue(
            db,
            order,
            "out_of_stock",
            remaining_original.id,
            Decimal("1"),
            None,
            None,
            "Remove the remaining original model",
            "vendor@example.com",
        )
        removal_issue = next(
            item
            for item in order.attention_items
            if item.status == "pending" and item.action_type == "out_of_stock"
        )
        order = remove_model_for_vendor_attention(db, order, removal_issue.id, "buyer@example.com")
        assert order.status == "vendor_attention"
        assert not any(line.product_code == "LIFE-1" for line in order.lines)
        removal_confirmation = next(
            item
            for item in order.attention_items
            if item.status == "pending" and item.action_type == "vendor_change_confirmation"
        )
        assert removal_confirmation.payload["resolution_action"] == "removed_out_of_stock_model"
        order = respond_to_attention(
            db,
            order,
            removal_confirmation.id,
            "confirm",
            "vendor",
            "vendor@example.com",
        )
        assert order.status == "active"

        order = create_purchasing_po_change(
            db,
            order,
            "request_eta",
            "buyer@example.com",
            "Please reconfirm delivery",
        )
        assert order.status == "vendor_attention"
        pending_attention = next(item for item in order.attention_items if item.status == "pending")
        order = respond_to_attention(
            db,
            order,
            pending_attention.id,
            "accept",
            "vendor",
            "vendor@example.com",
            date(2026, 8, 9),
        )
        assert order.status == "active"
        assert order.vendor_eta == date(2026, 8, 9)
        assert list_purchasing_pos(db, "active")[0].id == order.id
        order = receive_po_line(db, order, order.lines[0].id, Decimal("2"), "buyer@example.com")
        assert order.lines[0].received_quantity == 2
        handoff_purchase_order(db, order, "buyer@example.com")
        complete_reconciliation(db, order, "recon@example.com")
        assert order.status == "reconciliation_complete"


def test_bulk_vendor_order_creation_creates_one_draft_per_unique_store() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="V-BULK",
                name="Bulk Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        db.add_all(
            [
                Store(
                    store_number=number,
                    name=f"Store {number}",
                    region_code="EAST",
                    entity_code="ENTITY-1",
                    state_code="FL",
                    is_active=True,
                    is_ordering_enabled=True,
                )
                for number in ("101", "102")
            ]
        )
        db.add(
            CatalogProduct(
                product_code="BULK-1",
                vendor_code="V-BULK",
                name="Bulk Model",
                unit_price=Decimal("125.50"),
                currency="USD",
                minimum_order_quantity=1,
                is_available=True,
                is_active=True,
                source_file="test.xlsx",
            )
        )
        db.commit()

        requests = create_vendor_requests(
            db,
            "V-BULK",
            ["101", "102", "101"],
            "vendor@example.com",
            date(2026, 9, 1),
            [LifecycleLineWrite(product_code="BULK-1", quantity=3)],
        )

        assert [request.store_number for request in requests] == ["101", "102"]
        assert all(request.status == "vendor_draft" for request in requests)
        assert all(request.expected_delivery_date == date(2026, 9, 1) for request in requests)
        assert all(request.line_items[0].quantity == 3 for request in requests)
        assert all(request.total == Decimal("376.50") for request in requests)

        delete_vendor_request(db, requests[0])
        assert db.get(type(requests[0]), requests[0].id) is None
