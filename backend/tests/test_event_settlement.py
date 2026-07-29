from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.db.session import Base, get_db
from app.main import app
from app.models import catalog, event_management, identity, store  # noqa: F401
from app.models.catalog import CatalogVendor
from app.models.event_management import (
    EventEntityOrder,
    EventMembership,
    EventOrderBackupArtifact,
    EventPresentationState,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
    StoreLoadoutAssignment,
    StoreLoadoutEvent,
    StoreLoadoutItem,
)
from app.models.event_snapshot import EventSnapshot
from app.models.identity import User
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.schemas.event_management import EventWrite
from app.schemas.event_settlement import EventSettlementWrite
from app.services.admin_bootstrap_service import ensure_core_permissions, ensure_core_roles
from app.services.event_closeout_insights_service import (
    EventCloseoutInsightsError,
    event_closeout_insights,
)
from app.services.event_management_service import create_event
from app.services.event_settlement_service import (
    EventSettlementError,
    configure_event_settlement,
    event_settlement_export_rows,
    event_settlement_summary,
)


def _event() -> EventWrite:
    return EventWrite(
        name="Settlement Show 2027",
        slug="settlement-show-2027",
        starts_at=datetime(2027, 6, 1, 12, tzinfo=UTC),
        ends_at=datetime(2027, 6, 3, 20, tzinfo=UTC),
        venue_name="Convention Center",
        address_line1="100 Show Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
    )


def _seed(db: Session) -> tuple[User, User, str]:
    roles = ensure_core_roles(db, ensure_core_permissions(db))
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="test",
        is_active=True,
    )
    admin.roles = [roles["ADMIN"]]
    store_user = User(
        email="store@example.com",
        display_name="Store",
        password_hash="test",
        home_store_number="1001",
        is_active=True,
    )
    store_user.roles = [roles["FRANCHISE_OPERATOR"]]
    db.add_all(
        [
            admin,
            store_user,
            CatalogVendor(
                vendor_code="HALL",
                name="Hall Vendor",
                is_active=True,
                source_file="test",
            ),
        ]
    )
    db.commit()
    event = create_event(db, _event(), admin.email)
    sub_event = ManagedSubEvent(
        event_id=event.id,
        name="Buying floor",
        starts_at=datetime(2027, 6, 1, 14, tzinfo=UTC),
        ends_at=datetime(2027, 6, 1, 16, tzinfo=UTC),
        location="Hall A",
        module_codes=["ordering", "store-loadout", "event-settlement"],
    )
    db.add(sub_event)
    db.flush()
    slide = EventProductSlide(
        event_id=event.id,
        sub_event_id=sub_event.id,
        vendor_code="HALL",
        model_number="SS-200",
        name="Sleeper Sofa",
        event_unit_cost=Decimal("399.99"),
        standard_cost=Decimal("499.99"),
        minimum_order_quantity=1,
        delivery_window_start=date(2027, 6, 10),
        delivery_window_end=date(2027, 7, 1),
        position=1,
        created_by=admin.email,
    )
    db.add(slide)
    db.flush()
    db.add(
        EventEntityOrder(
            event_id=event.id,
            sub_event_id=sub_event.id,
            slide_id=slide.id,
            membership_id="membership-1",
            user_id=admin.id,
            entity_code="ENT-1",
            quantity=2,
            requested_delivery_start=date(2027, 6, 10),
            requested_delivery_end=date(2027, 7, 1),
            unit_cost=Decimal("399.99"),
            total_cost=Decimal("799.98"),
            status="confirmed",
            review_status="approved",
        )
    )
    loadout = StoreLoadoutEvent(event_id=event.id, status="open", created_by=admin.email)
    db.add(loadout)
    db.flush()
    assignment = StoreLoadoutAssignment(
        store_loadout_event_id=loadout.id,
        event_id=event.id,
        store_number="1001",
        entity_code="ENT-1",
        status="signed_complete",
        pickup_priority=1,
        assigned_by=admin.email,
        signed_at=datetime(2027, 6, 3, 18, tzinfo=UTC),
        signed_by=store_user.email,
    )
    db.add(assignment)
    db.flush()
    db.add(
        StoreLoadoutItem(
            assignment_id=assignment.id,
            event_id=event.id,
            vendor_hall_booth_id="booth-1",
            vendor_hall_inventory_item_id="inventory-1",
            vendor_code="HALL",
            booth_number="B-12",
            item_name="Sleeper Sofa",
            model_number="SS-200",
            quantity_assigned=2,
            quantity_found=2,
            condition="new",
            status="signed_off",
        )
    )
    db.commit()
    return admin, store_user, event.id


def test_event_settlement_summary_detects_closeout_exceptions() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)
        summary = configure_event_settlement(
            db,
            event_id,
            EventSettlementWrite(status="collecting_evidence", notes="Closing event."),
            admin.email,
        )
        assert summary is not None
        assert summary.order_total == 1
        assert summary.order_released == 0
        assert summary.approved_units == 2
        assert summary.loadout_assignment_total == 1
        assert summary.loadout_signed == 1
        assert summary.loadout_released == 0
        assert summary.loadout_final_review_pending == 0
        assert summary.status == "exceptions_present"
        assert {item.exception_type for item in summary.exceptions} == {
            "unreleased_order",
            "unreleased_store",
        }

        order = db.scalar(select(EventEntityOrder))
        assignment = db.scalar(select(StoreLoadoutAssignment))
        assert order is not None
        assert assignment is not None
        order.review_status = "released"
        assignment.status = "released_from_venue"
        db.commit()

        ready = event_settlement_summary(db, event_id)
        assert ready is not None
        assert ready.status == "ready_for_review"
        assert ready.readiness_percentage == Decimal("100.00")
        assert ready.open_exception_count == 0


def test_cancelled_event_settlement_is_read_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)
        event = db.get(ManagedEvent, event_id)
        assert event is not None
        event.status = "cancelled"
        db.commit()

        with pytest.raises(EventSettlementError, match="read-only"):
            configure_event_settlement(
                db,
                event_id,
                EventSettlementWrite(
                    status="collecting_evidence",
                    notes="Attempted after cancellation.",
                ),
                admin.email,
            )


def test_event_settlement_includes_vendor_buy_fair_orders_without_double_counting() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)
        request = PurchaseRequest(
            order_number="Settlement Show 2027-1001-HALL-001",
            workflow_code="VENDOR_ORDER",
            store_number="1001",
            vendor_code="HALL",
            status="vendor_draft",
            subtotal=Decimal("300.00"),
            total=Decimal("300.00"),
            context={
                "source": "event_vendor_buy_fair",
                "event_id": event_id,
                "event_name": "Settlement Show 2027",
            },
            created_by=admin.email,
            updated_by=admin.email,
        )
        request.line_items.append(
            PurchaseRequestLineItem(
                product_code="SS-200",
                product_name="Sleeper Sofa",
                quantity=3,
                unit_price=Decimal("100.00"),
                extended_amount=Decimal("300.00"),
            )
        )
        db.add(request)
        db.commit()

        draft = event_settlement_summary(db, event_id)
        assert draft is not None
        assert draft.order_total == 2
        assert draft.order_released == 0
        assert draft.approved_units == 2
        assert draft.approved_spend == Decimal("799.98")
        assert "unsubmitted_buy_fair_order" in {item.exception_type for item in draft.exceptions}

        request.status = "submitted_to_purchasing"
        db.commit()
        submitted = event_settlement_summary(db, event_id)
        assert submitted is not None
        assert submitted.order_total == 2
        assert submitted.order_released == 1
        assert submitted.approved_units == 5
        assert submitted.approved_spend == Decimal("1099.98")
        assert "unsubmitted_buy_fair_order" not in {
            item.exception_type for item in submitted.exceptions
        }
        headers, rows = event_settlement_export_rows(db, event_id, "order-closeout") or ([], [])
        assert "order_channel" in headers
        buy_fair_row = next(row for row in rows if row[14] == "vendor_buy_fair")
        assert buy_fair_row[1] == "1001"
        assert buy_fair_row[2] == "HALL"
        assert buy_fair_row[5] == "3"
        assert buy_fair_row[8] == "submitted_to_purchasing"
        assert buy_fair_row[15] == request.order_number

        request.status = "cancelled_by_vendor"
        db.commit()
        cancelled = event_settlement_summary(db, event_id)
        assert cancelled is not None
        assert cancelled.order_total == 1
        assert cancelled.approved_units == 2


def test_event_settlement_flags_loadout_final_review_pending() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _admin, _store_user, event_id = _seed(db)
        assignment = db.scalar(select(StoreLoadoutAssignment))
        assert assignment is not None
        assignment.status = "ready_for_final_review"
        assignment.final_review_requested_at = datetime(2027, 6, 3, 17, tzinfo=UTC)
        assignment.final_review_requested_by = "store@example.com"
        assignment.team_name = "Team Alpha"
        assignment.team_lead_emails = ["lead@example.com"]
        db.commit()

        summary = event_settlement_summary(db, event_id)

        assert summary is not None
        assert summary.loadout_final_review_pending == 1
        assert "loadout_final_review_pending" in {
            item.exception_type for item in summary.exceptions
        }
        pending = next(
            item
            for item in summary.exceptions
            if item.exception_type == "loadout_final_review_pending"
        )
        assert pending.reference_id == assignment.id
        assert "lead@example.com" in pending.description


def test_event_settlement_detects_order_loadout_mismatches() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _admin, _store_user, event_id = _seed(db)
        order = db.scalar(select(EventEntityOrder))
        assignment = db.scalar(select(StoreLoadoutAssignment))
        item = db.scalar(select(StoreLoadoutItem))
        assert order is not None
        assert assignment is not None
        assert item is not None
        order.review_status = "released"
        assignment.status = "released_from_venue"
        item.quantity_assigned = 1
        db.commit()

        summary = event_settlement_summary(db, event_id)

        assert summary is not None
        assert summary.quantity_mismatch_count == 1
        assert "quantity_mismatch" in {exception.exception_type for exception in summary.exceptions}

        item.model_number = "SS-404"
        db.commit()

        summary = event_settlement_summary(db, event_id)

        assert summary is not None
        assert summary.ordered_not_loaded_count == 1
        assert summary.loaded_not_ordered_count == 1
        assert summary.quantity_mismatch_count == 0
        exception_types = {exception.exception_type for exception in summary.exceptions}
        assert "ordered_not_loaded" in exception_types
        assert "loaded_not_ordered" in exception_types


def test_event_settlement_blocks_approval_until_ready() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            client = TestClient(app)
            response = client.put(
                f"/api/v1/event-settlement/events/{event_id}",
                json={"status": "approved", "notes": "Trying to close early."},
            )
            assert response.status_code == 422
            assert "open exceptions" in response.json()["detail"]

            order = db.scalar(select(EventEntityOrder))
            assignment = db.scalar(select(StoreLoadoutAssignment))
            assert order is not None
            assert assignment is not None
            order.review_status = "released"
            assignment.status = "released_from_venue"
            sub_event = db.scalar(
                select(ManagedSubEvent).where(ManagedSubEvent.event_id == event_id)
            )
            assert sub_event is not None
            presentation = EventPresentationState(
                sub_event_id=sub_event.id,
                event_id=event_id,
                status="live",
                ordering_status="open",
                updated_by=admin.email,
            )
            db.add(presentation)
            db.commit()

            response = client.put(
                f"/api/v1/event-settlement/events/{event_id}",
                json={"status": "approved", "notes": "Ready for finance."},
            )
            assert response.status_code == 200
            approved_payload = response.json()
            assert approved_payload["status"] == "approved"
            assert approved_payload["approved_at"] is not None
            assert approved_payload["approved_by"] == admin.email
            assert approved_payload["notes"] == "Ready for finance."

            response = client.put(
                f"/api/v1/event-settlement/events/{event_id}",
                json={"status": "closed", "notes": "Settlement packet closed."},
            )
            assert response.status_code == 200
            closed_payload = response.json()
            assert closed_payload["status"] == "closed"
            assert closed_payload["approved_by"] == admin.email
            assert closed_payload["closed_at"] is not None
            assert closed_payload["closed_by"] == admin.email
            assert db.get(ManagedEvent, event_id).status == "completed"
            db.refresh(sub_event)
            db.refresh(presentation)
            assert sub_event.status == "completed"
            assert presentation.status == "ended"
            assert presentation.ordering_status == "closed"
            artifact = db.scalar(
                select(EventOrderBackupArtifact).where(
                    EventOrderBackupArtifact.event_id == event_id
                )
            )
            assert artifact is not None
            assert artifact.created_by == admin.email
            assert artifact.sha256 == sha256(artifact.content).hexdigest()
            assert artifact.size_bytes == len(artifact.content)
            archived_response = client.get(
                f"/api/v1/event-order-review/{event_id}/archived-backup.xlsx"
            )
            assert archived_response.status_code == 200
            assert archived_response.content == artifact.content
            assert archived_response.headers["x-btsp-content-sha256"] == artifact.sha256
            metadata_response = client.get(f"/api/v1/event-order-review/{event_id}/archived-backup")
            assert metadata_response.status_code == 200
            assert metadata_response.json()["id"] == artifact.id
            assert metadata_response.json()["sha256"] == artifact.sha256
            assert metadata_response.json()["size_bytes"] == artifact.size_bytes

            response = client.put(
                f"/api/v1/events/{event_id}",
                json=_event().model_dump(mode="json"),
            )
            assert response.status_code == 409
            assert "configuration is locked" in response.json()["detail"]
            response = client.put(
                f"/api/v1/events/{event_id}/sub-events/{sub_event.id}/modules",
                json={"module_codes": ["ordering"]},
            )
            assert response.status_code == 422
            assert "configuration is locked" in response.json()["detail"]
            response = client.post(
                f"/api/v1/event-announcements/{event_id}",
                json={
                    "title": "Late notice",
                    "body": "This should not be saved.",
                    "severity": "info",
                    "visibility_categories": ["executive"],
                    "publishes_at": "2027-06-04T12:00:00Z",
                },
            )
            assert response.status_code == 422
            assert "announcements are locked" in response.json()["detail"]
            response = client.post(
                f"/api/v1/event-calendar/{event_id}",
                json={
                    "entry_type": "text",
                    "title": "Late calendar change",
                    "starts_at": "2027-06-04T12:00:00Z",
                    "ends_at": "2027-06-04T13:00:00Z",
                    "visibility_categories": ["executive"],
                },
            )
            assert response.status_code == 422
            assert "calendar is locked" in response.json()["detail"]
            assert client.get(f"/api/v1/event-announcements/{event_id}").status_code == 200
            assert client.get(f"/api/v1/event-calendar/{event_id}").status_code == 200
            response = client.put(
                f"/api/v1/store-loadout/events/{event_id}",
                json={"status": "open", "default_loadout_zone": "Late zone"},
            )
            assert response.status_code == 422
            assert "loadout is locked" in response.json()["detail"]
            response = client.put(
                f"/api/v1/vendor-hall/events/{event_id}",
                json={"status": "open"},
            )
            assert response.status_code == 422
            assert "Vendor hall is locked" in response.json()["detail"]

            response = client.put(
                f"/api/v1/event-settlement/events/{event_id}",
                json={"status": "collecting_evidence", "notes": "Reopen."},
            )
            assert response.status_code == 422
            assert "cannot be reopened" in response.json()["detail"]
            response = client.post(
                f"/api/v1/event-settlement/events/{event_id}/exceptions",
                json={
                    "exception_type": "late_change",
                    "severity": "medium",
                    "description": "Attempted after close.",
                },
            )
            assert response.status_code == 422
            assert "cannot be changed" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_event_settlement_exports_closeout_reports() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)
        configure_event_settlement(
            db,
            event_id,
            EventSettlementWrite(status="collecting_evidence", notes="Closing event."),
            admin.email,
        )

        summary_headers, summary_rows = event_settlement_export_rows(db, event_id, "summary") or (
            [],
            [],
        )
        assert summary_headers == ["metric", "value"]
        assert ["event_name", "Settlement Show 2027"] in summary_rows
        assert any(row[0] == "approved_at" for row in summary_rows)
        assert any(row[0] == "closed_by" for row in summary_rows)
        assert any(row[0] == "quantity_mismatch_count" for row in summary_rows)

        exception_headers, exception_rows = event_settlement_export_rows(
            db, event_id, "exceptions"
        ) or ([], [])
        assert "exception_type" in exception_headers
        assert {row[1] for row in exception_rows} == {
            "unreleased_order",
            "unreleased_store",
        }

        order_headers, order_rows = event_settlement_export_rows(
            db, event_id, "order-closeout"
        ) or ([], [])
        assert "review_status" in order_headers
        assert order_rows[0][1] == "ENT-1"
        assert order_rows[0][3] == "SS-200"

        loadout_headers, loadout_rows = event_settlement_export_rows(
            db, event_id, "loadout-closeout"
        ) or ([], [])
        assert "assignment_status" in loadout_headers
        assert "team_lead_emails" in loadout_headers
        assert "final_review_requested_at" in loadout_headers
        assert "final_review_completed_at" in loadout_headers
        assert "final_review_notes" in loadout_headers
        assert loadout_rows[0][1] == "1001"

        reconciliation_headers, reconciliation_rows = event_settlement_export_rows(
            db, event_id, "reconciliation-detail"
        ) or ([], [])
        assert "variance" in reconciliation_headers
        assert reconciliation_rows == []

        audit_headers, audit_rows = event_settlement_export_rows(db, event_id, "audit-log") or (
            [],
            [],
        )
        assert "action" in audit_headers
        assert audit_rows[0][2] == "event_settlement.configured"

        packet_headers, packet_rows = event_settlement_export_rows(
            db, event_id, "closeout-packet"
        ) or ([], [])
        assert packet_headers == ["section", "row_number", "field", "value"]
        assert {"summary", "exceptions", "order_closeout", "loadout_closeout", "audit_log"} <= {
            row[0] for row in packet_rows
        }
        assert "reconciliation_detail" in {row[0] for row in packet_rows}
        assert ["summary", "2", "metric", "event_name"] in packet_rows
        assert ["summary", "2", "value", "Settlement Show 2027"] in packet_rows
        assert any(row[:3] == ["order_closeout", "1", "model_number"] for row in packet_rows)


def test_event_settlement_reconciliation_detail_export_lists_variances() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _admin, _store_user, event_id = _seed(db)
        order = db.scalar(select(EventEntityOrder))
        assignment = db.scalar(select(StoreLoadoutAssignment))
        item = db.scalar(select(StoreLoadoutItem))
        assert order is not None
        assert assignment is not None
        assert item is not None
        order.review_status = "released"
        assignment.status = "released_from_venue"
        item.quantity_assigned = 1
        db.commit()

        headers, rows = event_settlement_export_rows(db, event_id, "reconciliation-detail") or (
            [],
            [],
        )

        assert headers == [
            "event",
            "entity_code",
            "vendor_code",
            "model_number",
            "released_order_quantity",
            "released_loadout_quantity",
            "variance",
            "exception_type",
        ]
        assert rows == [
            [
                "Settlement Show 2027",
                "ENT-1",
                "HALL",
                "SS-200",
                "2",
                "1",
                "-1",
                "quantity_mismatch",
            ]
        ]


def test_event_settlement_manual_exception_lifecycle() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, _store_user, event_id = _seed(db)
        order = db.scalar(select(EventEntityOrder))
        assignment = db.scalar(select(StoreLoadoutAssignment))
        assert order is not None
        assert assignment is not None
        order.review_status = "released"
        assignment.status = "released_from_venue"
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            client = TestClient(app)
            response = client.post(
                f"/api/v1/event-settlement/events/{event_id}/exceptions",
                json={
                    "exception_type": "finance_review",
                    "severity": "high",
                    "reference_type": "manual",
                    "reference_id": "FIN-1",
                    "description": "Finance needs final invoice backup.",
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "exceptions_present"
            manual = next(
                item for item in payload["exceptions"] if item["exception_type"] == "finance_review"
            )
            assert manual["status"] == "open"

            response = client.post(
                f"/api/v1/event-settlement/exceptions/{manual['id']}/resolve",
                json={"resolution_notes": "Invoice backup attached."},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "ready_for_review"
            resolved = next(item for item in payload["exceptions"] if item["id"] == manual["id"])
            assert resolved["status"] == "resolved"
            assert resolved["resolution_notes"] == "Invoice backup attached."

            response = client.post(f"/api/v1/event-settlement/exceptions/{manual['id']}/reopen")
            assert response.status_code == 200
            reopened = next(
                item for item in response.json()["exceptions"] if item["id"] == manual["id"]
            )
            assert reopened["status"] == "open"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_event_settlement_routes_require_settlement_permissions() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin, store_user, event_id = _seed(db)

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: store_user
        try:
            client = TestClient(app)
            response = client.get(f"/api/v1/event-settlement/events/{event_id}/summary")
            assert response.status_code == 403
            response = client.get(f"/api/v1/event-order-review/{event_id}/backup.xlsx")
            assert response.status_code == 403

            app.dependency_overrides[get_current_user] = lambda: admin
            response = client.put(
                f"/api/v1/event-settlement/events/{event_id}",
                json={"status": "collecting_evidence", "notes": "Closeout started."},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "exceptions_present"

            response = client.get(f"/api/v1/event-settlement/events/{event_id}/exports/summary")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/csv")
            assert "event_name" in response.text

            response = client.get(f"/api/v1/event-order-review/{event_id}/backup.xlsx")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            digest = sha256(response.content).hexdigest()
            assert response.headers["x-btsp-content-sha256"] == digest
            audit = db.scalar(
                select(EventSnapshot).where(
                    EventSnapshot.event_type == "event.order_backup.exported",
                    EventSnapshot.entity_id == event_id,
                )
            )
            assert audit is not None
            assert audit.actor == admin.email
            assert audit.payload["sha256"] == digest
            assert audit.payload["size_bytes"] == len(response.content)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_executive_closeout_insights_are_event_scoped() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _admin, outsider, event_id = _seed(db)
        executive = User(
            email="executive@example.com",
            display_name="Event Executive",
            password_hash="test",
            is_active=True,
        )
        db.add(executive)
        db.flush()
        db.add(
            EventMembership(
                event_id=event_id,
                user_id=executive.id,
                membership_type="executive",
                module_codes=["event-settlement"],
                is_active=True,
            )
        )
        db.commit()

        insights = event_closeout_insights(db, event_id, executive)
        assert insights is not None
        assert insights.event_id == event_id
        assert insights.order_total == 1
        assert insights.approved_spend == Decimal("799.98")
        assert insights.open_exception_count > 0
        with pytest.raises(EventCloseoutInsightsError, match="not assigned"):
            event_closeout_insights(db, event_id, outsider)
