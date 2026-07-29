from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.event_realtime import _realtime_access_allowed
from app.auth.dependencies import get_current_user
from app.db.session import Base, get_db
from app.main import app
from app.models import (  # noqa: F401
    analytics,
    attachment,
    catalog,
    configuration,
    event_management,
    event_snapshot,
    identity,
    invoice_intake,
    notification,
    purchase_order,
    purchasing,
    receiving,
    store,
    vendor_integration,
    workflow,
)
from app.models.catalog import CatalogVendor
from app.models.event_management import ManagedEvent
from app.models.identity import Permission, Role, User
from app.models.store import Store
from app.schemas.event_announcement import EventAnnouncementWrite
from app.schemas.event_management import EventMembershipCreate, EventWrite, SubEventWrite
from app.schemas.event_poll import EventPollCreate
from app.schemas.event_vendor_booth import EventVendorBoothWrite
from app.services.event_announcement_service import save_announcement
from app.services.event_management_service import add_membership, add_sub_event, create_event
from app.services.event_poll_service import create_poll, set_poll_status
from app.services.event_vendor_booth_service import save_booth


def test_only_explicit_bootstrap_and_probe_routes_are_public() -> None:
    public_operations = {
        (method.upper(), path)
        for path, methods in app.openapi()["paths"].items()
        for method, operation in methods.items()
        if method != "parameters" and not operation.get("security")
    }

    assert public_operations == {
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/ready"),
        ("GET", "/api/v1/system/version"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/password-reset/request"),
        ("POST", "/api/v1/auth/password-reset/confirm"),
        ("POST", "/api/v1/bootstrap/admin"),
    }
    assert TestClient(app).get("/api/v1/health").headers["cache-control"] == "no-store"


def test_completed_event_realtime_channel_is_closed_to_managers() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permission = Permission(code="events.manage", description="Manage events")
        role = Role(code="EVENT_MANAGER", name="Event Manager", permissions=[permission])
        manager = User(
            email="event.manager@example.com",
            display_name="Event Manager",
            password_hash="not-used",
            is_active=True,
            roles=[role],
        )
        db.add(manager)
        event = create_event(
            db,
            EventWrite(
                name="Realtime Lifecycle Test",
                slug="realtime-lifecycle-test",
                starts_at=datetime(2027, 1, 10, 12, tzinfo=UTC),
                ends_at=datetime(2027, 1, 11, 12, tzinfo=UTC),
                venue_name="Test Hall",
                address_line1="1 Test Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            manager.email,
        )
        event = add_sub_event(
            db,
            event.id,
            SubEventWrite(
                name="Realtime Session",
                starts_at=datetime(2027, 1, 10, 14, tzinfo=UTC),
                ends_at=datetime(2027, 1, 10, 15, tzinfo=UTC),
                location="Ballroom",
                module_codes=["live-display"],
            ),
        )
        assert event is not None
        sub_event_id = event.sub_events[0].id
        assert _realtime_access_allowed(db, manager.email, sub_event_id)

        event_record = db.get(ManagedEvent, event.id)
        assert event_record is not None
        event_record.status = "completed"
        db.commit()

        assert not _realtime_access_allowed(db, manager.email, sub_event_id)


def test_event_member_resources_are_blocked_after_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Store(
                store_number="9001",
                name="Past Event Store",
                region_code="R1",
                entity_code="ENTITY-PAST",
                is_ordering_enabled=True,
                is_active=True,
            )
        )
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Past Leadership Meeting",
                slug="past-leadership-meeting",
                starts_at=datetime(2020, 1, 10, 12, tzinfo=UTC),
                ends_at=datetime(2020, 1, 11, 12, tzinfo=UTC),
                venue_name="Past Hall",
                address_line1="1 Archive Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        event = add_sub_event(
            db,
            event.id,
            SubEventWrite(
                name="Past Live Buying",
                starts_at=datetime(2020, 1, 10, 14, tzinfo=UTC),
                ends_at=datetime(2020, 1, 10, 15, tzinfo=UTC),
                location="Ballroom",
                module_codes=["live-display"],
            ),
        )
        assert event is not None
        sub_event_id = event.sub_events[0].id
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="past.rep@example.com",
                display_name="Past Rep",
                password="Past-Event-Pass!",
                membership_type="franchise_representative",
                entity_code="ENTITY-PAST",
                module_codes=["live-display"],
            ),
        )
        attendee = db.scalar(select(User).where(User.email == "past.rep@example.com"))
        assert attendee is not None
        assert not _realtime_access_allowed(db, attendee.email, sub_event_id)

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: attendee
        try:
            response = TestClient(app).get(f"/api/v1/event-presentations/{sub_event_id}")
            assert response.status_code == 403
            assert response.json()["detail"] == "Event access is required"

            branding_response = TestClient(app).get(f"/api/v1/events/{event.id}/branding")
            assert branding_response.status_code == 403
            assert branding_response.json()["detail"] == "Event access is required"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_my_event_announcements_are_hidden_after_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Store(
                store_number="9002",
                name="Expired Announcement Store",
                region_code="R1",
                entity_code="ENTITY-EXPIRED",
                is_ordering_enabled=True,
                is_active=True,
            )
        )
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Expired Vendor Fair",
                slug="expired-vendor-fair",
                starts_at=datetime(2020, 2, 10, 12, tzinfo=UTC),
                ends_at=datetime(2020, 2, 11, 12, tzinfo=UTC),
                venue_name="Past Hall",
                address_line1="1 Archive Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        save_announcement(
            db,
            event.id,
            EventAnnouncementWrite(
                title="Expired event update",
                body="This should not appear after the event window.",
                severity="important",
                visibility_categories=["franchise_representative"],
                publishes_at=datetime(2020, 2, 10, 13, tzinfo=UTC),
            ),
            "admin@example.com",
        )
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="expired.rep@example.com",
                display_name="Expired Rep",
                password="Past-Event-Pass!",
                membership_type="franchise_representative",
                entity_code="ENTITY-EXPIRED",
                module_codes=["check-in"],
            ),
        )
        attendee = db.scalar(select(User).where(User.email == "expired.rep@example.com"))
        assert attendee is not None

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: attendee
        try:
            response = TestClient(app).get("/api/v1/event-announcements/mine")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_event_polls_are_blocked_after_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Store(
                store_number="9003",
                name="Expired Poll Store",
                region_code="R1",
                entity_code="ENTITY-POLL",
                is_ordering_enabled=True,
                is_active=True,
            )
        )
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Expired Poll Event",
                slug="expired-poll-event",
                starts_at=datetime(2020, 3, 10, 12, tzinfo=UTC),
                ends_at=datetime(2020, 3, 11, 12, tzinfo=UTC),
                venue_name="Past Hall",
                address_line1="1 Archive Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        event = add_sub_event(
            db,
            event.id,
            SubEventWrite(
                name="Expired Poll Session",
                starts_at=datetime(2020, 3, 10, 14, tzinfo=UTC),
                ends_at=datetime(2020, 3, 10, 15, tzinfo=UTC),
                location="Ballroom",
                module_codes=["polling"],
            ),
        )
        assert event is not None
        sub_event_id = event.sub_events[0].id
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="expired.poll.rep@example.com",
                display_name="Expired Poll Rep",
                password="Past-Event-Pass!",
                membership_type="franchise_representative",
                entity_code="ENTITY-POLL",
                module_codes=["polling"],
            ),
        )
        poll = create_poll(
            db,
            sub_event_id,
            EventPollCreate(question="Can you see this?", options=["Yes", "No"]),
            "admin@example.com",
        )
        assert poll is not None
        poll = set_poll_status(db, poll.id, "open")
        assert poll is not None
        attendee = db.scalar(select(User).where(User.email == "expired.poll.rep@example.com"))
        assert attendee is not None

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: attendee
        try:
            client = TestClient(app)
            active_response = client.get(f"/api/v1/event-polls/active/{sub_event_id}")
            assert active_response.status_code == 403
            assert active_response.json()["detail"] == (
                "Event access is outside the scheduled window"
            )

            vote_response = client.post(
                f"/api/v1/event-polls/{poll.id}/vote",
                json={"option_id": poll.options[0].id},
            )
            assert vote_response.status_code == 403
            assert vote_response.json()["detail"] == (
                "Event access is outside the scheduled window"
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_vendor_booth_self_update_is_blocked_after_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="VEND-EXPIRED",
                name="Expired Vendor",
                is_active=True,
                source_file="test",
            )
        )
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Expired Vendor Booth Event",
                slug="expired-vendor-booth-event",
                starts_at=datetime(2020, 4, 10, 12, tzinfo=UTC),
                ends_at=datetime(2020, 4, 11, 12, tzinfo=UTC),
                venue_name="Past Hall",
                address_line1="1 Archive Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="expired.vendor@example.com",
                display_name="Expired Vendor",
                password="Past-Event-Pass!",
                membership_type="vendor",
                vendor_code="VEND-EXPIRED",
                module_codes=["vendor-booths"],
            ),
        )
        booth = save_booth(
            db,
            event.id,
            EventVendorBoothWrite(
                vendor_code="VEND-EXPIRED",
                booth_name="Expired Vendor Booth",
                booth_number="B-10",
                location="North Hall",
                description="Original booth profile.",
                status="published",
            ),
            "admin@example.com",
        )
        assert booth is not None
        vendor_user = db.scalar(select(User).where(User.email == "expired.vendor@example.com"))
        assert vendor_user is not None

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: vendor_user
        try:
            response = TestClient(app).put(
                f"/api/v1/event-vendor-booths/mine/{booth.id}",
                json={
                    "vendor_code": "VEND-EXPIRED",
                    "booth_name": "Expired Vendor Booth Updated",
                    "booth_number": "B-10",
                    "location": "North Hall",
                    "description": "This update should be blocked.",
                    "status": "published",
                },
            )
            assert response.status_code == 403
            assert response.json()["detail"] == ("Event access is outside the scheduled window")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_vendor_buy_fair_workspace_is_blocked_after_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="BUY-FAIR-EXPIRED",
                name="Expired Buy Fair Vendor",
                is_active=True,
                source_file="test",
            )
        )
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Expired Vendor Buy Fair",
                slug="expired-vendor-buy-fair",
                starts_at=datetime(2020, 5, 10, 12, tzinfo=UTC),
                ends_at=datetime(2020, 5, 11, 12, tzinfo=UTC),
                venue_name="Past Hall",
                address_line1="1 Archive Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        event = add_sub_event(
            db,
            event.id,
            SubEventWrite(
                name="Expired Vendor Ordering",
                starts_at=datetime(2020, 5, 10, 14, tzinfo=UTC),
                ends_at=datetime(2020, 5, 10, 15, tzinfo=UTC),
                location="Vendor Hall",
                module_codes=["vendor-buy-fair"],
            ),
        )
        assert event is not None
        sub_event_id = event.sub_events[0].id
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="expired.buyfair.vendor@example.com",
                display_name="Expired Buy Fair Vendor",
                password="Past-Event-Pass!",
                membership_type="vendor",
                vendor_code="BUY-FAIR-EXPIRED",
                module_codes=["vendor-buy-fair"],
            ),
        )
        vendor_user = db.scalar(
            select(User).where(User.email == "expired.buyfair.vendor@example.com")
        )
        assert vendor_user is not None

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: vendor_user
        try:
            response = TestClient(app).get(f"/api/v1/event-buy-fair/{sub_event_id}")
            assert response.status_code == 403
            assert response.json()["detail"] == ("Event access is outside the scheduled window")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
