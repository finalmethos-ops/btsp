from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.db.session import Base
from app.models import (  # noqa: F401
    catalog,
    event_management,
    identity,
    purchasing,
    store,
    workflow,
)
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_management import (
    EventAnnouncement,
    EventCalendarEntry,
    EventMembership,
    EventProductSlide,
    EventSettlementEvent,
    ManagedSubEvent,
    StoreLoadoutAssignment,
    StoreLoadoutItem,
    VendorHallBooth,
    VendorHallEvent,
    VendorHallInventoryItem,
)
from app.models.identity import User
from app.models.store import Store
from app.services.event_access_service import event_window_open_for_user
from app.services.event_demo_service import (
    DEMO_ACCOUNTS,
    seed_event_demo_accounts,
    seed_event_demo_event,
)
from app.services.store_loadout_service import my_store_loadout_assignments
from app.services.vendor_hall_service import my_vendor_hall_booths


def test_event_demo_seed_is_complete_and_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = seed_event_demo_accounts(db, "BTSP-Demo-Test-2026!")
        second = seed_event_demo_accounts(db, "BTSP-Demo-Test-2026!")

        assert first == second == list(DEMO_ACCOUNTS)
        assert db.scalar(select(User).where(User.email == "staff.demo@btsp.local"))
        assert len(db.scalars(select(User)).all()) == 5
        vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == "PERF-001"))
        assert vendor is not None and vendor.is_active is True
        assert (
            len(
                db.scalars(
                    select(CatalogProduct).where(CatalogProduct.vendor_code == "PERF-001")
                ).all()
            )
            == 3
        )
        for account in DEMO_ACCOUNTS:
            user = db.scalar(select(User).where(User.email == account.email))
            assert user is not None and user.is_active is True
            assert [role.code for role in user.roles] == [account.role_code]
            assert verify_password("BTSP-Demo-Test-2026!", user.password_hash)
        demo_store = db.scalar(select(Store).where(Store.store_number == "0002"))
        assert demo_store is not None
        assert demo_store.entity_code == "BEBE"


def test_full_event_uat_seed_is_complete_and_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = seed_event_demo_event(db, "BTSP-Demo-Test-2026!")
        second = seed_event_demo_event(db, "BTSP-Demo-Test-2026!")
        assert first.id == second.id
        assert first.slug == "btsp-uat-demo-2026"
        sub_events = db.scalars(
            select(ManagedSubEvent).where(ManagedSubEvent.event_id == first.id)
        ).all()
        assert len(sub_events) == 4
        calendar_entries = db.scalars(
            select(EventCalendarEntry).where(EventCalendarEntry.event_id == first.id)
        ).all()
        assert len(calendar_entries) == 5
        assert len([item for item in calendar_entries if item.sub_event_id]) == 4
        assert {item.title for item in calendar_entries if not item.sub_event_id} == {
            "Welcome and event registration"
        }
        announcements = db.scalars(
            select(EventAnnouncement).where(EventAnnouncement.event_id == first.id)
        ).all()
        assert len(announcements) == 1
        assert announcements[0].visibility_categories == [
            "admin",
            "executive",
            "franchise_representative",
            "staff",
            "vendor",
        ]
        assert {code for item in sub_events for code in item.module_codes} >= {
            "vendor-hall-setup",
            "live-display",
            "ordering",
            "store-loadout",
            "event-settlement",
            "vendor-buy-fair",
        }
        assert (
            len(
                db.scalars(
                    select(EventMembership).where(EventMembership.event_id == first.id)
                ).all()
            )
            == 5
        )
        slides = db.scalars(
            select(EventProductSlide).where(EventProductSlide.event_id == first.id)
        ).all()
        assert len(slides) == 3
        assert {slide.status for slide in slides} == {"ready"}
        assert db.scalar(select(VendorHallEvent).where(VendorHallEvent.event_id == first.id))
        assert db.scalar(select(VendorHallBooth).where(VendorHallBooth.event_id == first.id))
        assert (
            len(
                db.scalars(
                    select(VendorHallInventoryItem).where(
                        VendorHallInventoryItem.event_id == first.id
                    )
                ).all()
            )
            == 3
        )
        assignments = db.scalars(
            select(StoreLoadoutAssignment).where(StoreLoadoutAssignment.event_id == first.id)
        ).all()
        assert len(assignments) == 1
        assert assignments[0].team_lead_emails == ["staff.demo@btsp.local"]
        assert (
            len(
                db.scalars(
                    select(StoreLoadoutItem).where(StoreLoadoutItem.event_id == first.id)
                ).all()
            )
            == 3
        )
        assert db.scalar(
            select(EventSettlementEvent).where(EventSettlementEvent.event_id == first.id)
        )
        staff = db.scalar(select(User).where(User.email == "staff.demo@btsp.local"))
        franchise = db.scalar(select(User).where(User.email == "franchise.demo@btsp.local"))
        assert staff is not None and franchise is not None
        assert len(my_vendor_hall_booths(db, staff)) == 1
        assert len(my_store_loadout_assignments(db, staff)) == 1
        assert len(my_store_loadout_assignments(db, franchise)) == 1
        vendor_user = db.scalar(select(User).where(User.email == "vendor.demo@btsp.local"))
        executive = db.scalar(select(User).where(User.email == "executive.demo@btsp.local"))
        assert vendor_user is not None and executive is not None
        assert event_window_open_for_user(
            db, first.id, vendor_user.id, datetime(2026, 8, 11, tzinfo=UTC)
        )
        assert not event_window_open_for_user(
            db, first.id, vendor_user.id, datetime(2026, 8, 1, tzinfo=UTC)
        )
        assert not event_window_open_for_user(
            db, first.id, vendor_user.id, datetime(2026, 8, 14, tzinfo=UTC)
        )
        assert event_window_open_for_user(db, first.id, staff.id, datetime(2026, 8, 1, tzinfo=UTC))
        assert event_window_open_for_user(
            db, first.id, executive.id, datetime(2026, 8, 14, tzinfo=UTC)
        )
