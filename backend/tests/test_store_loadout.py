from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.db.session import Base, get_db
from app.main import app
from app.models import (  # noqa: F401
    catalog,
    event_management,
    identity,
    store,
)
from app.models.catalog import CatalogVendor
from app.models.event_management import StoreLoadoutItemCheckin, VendorHallItemCheckin
from app.models.identity import User
from app.models.store import Store
from app.schemas.event_management import EVENT_MODULES, EventWrite
from app.schemas.event_vendor_booth import EventVendorBoothWrite
from app.schemas.store_loadout import (
    StoreLoadoutAssignmentWrite,
    StoreLoadoutEventWrite,
    StoreLoadoutFinalReviewWrite,
    StoreLoadoutItemAssignmentWrite,
    StoreLoadoutItemCheckinWrite,
    StoreLoadoutSignoffWrite,
    StoreLoadoutTeamWrite,
    StoreLoadoutVehicleStatusWrite,
)
from app.schemas.vendor_hall import VendorHallEventWrite, VendorHallInventoryItemWrite
from app.services.admin_bootstrap_service import ensure_core_permissions, ensure_core_roles
from app.services.event_management_service import create_event
from app.services.event_vendor_booth_service import save_booth
from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS, CORE_ROLE_DEFINITIONS
from app.services.store_loadout_service import (
    StoreLoadoutAccessError,
    StoreLoadoutError,
    assign_store_loadout_team,
    checkin_store_loadout_item,
    complete_store_loadout_final_review,
    configure_store_loadout,
    create_store_loadout_assignment,
    latest_store_loadout_signoff,
    mark_store_loadout_assignment_ready,
    my_store_loadout_assignments,
    release_store_loadout_assignment,
    sign_store_loadout_assignment,
    store_loadout_export_rows,
    store_loadout_summary,
    update_store_loadout_vehicle_status,
)
from app.services.vendor_hall_service import (
    configure_vendor_hall,
    create_booth_inventory_item,
    sync_vendor_hall_booths,
)


def _event() -> EventWrite:
    return EventWrite(
        name="Loadout Show 2027",
        slug="loadout-show-2027",
        starts_at=datetime(2027, 5, 1, 12, tzinfo=UTC),
        ends_at=datetime(2027, 5, 3, 20, tzinfo=UTC),
        venue_name="Convention Center",
        address_line1="100 Show Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
    )


def _seed_foundation(db: Session) -> None:
    roles = ensure_core_roles(db, ensure_core_permissions(db))
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="test",
        is_active=True,
    )
    admin.roles = [roles["ADMIN"]]
    db.add(admin)
    db.add_all(
        [
            CatalogVendor(
                vendor_code="HALL",
                name="Hall Vendor",
                is_active=True,
                source_file="test",
            ),
            Store(
                store_number="1001",
                name="Buddy's 1001",
                region_code="FL",
                entity_code="ENT-1",
                is_active=True,
                is_ordering_enabled=True,
            ),
        ]
    )
    db.commit()


def _seed_vendor_hall_item(db: Session) -> tuple[str, str]:
    event = create_event(db, _event(), "admin@example.com")
    save_booth(
        db,
        event.id,
        EventVendorBoothWrite(
            vendor_code="HALL",
            booth_name="Hall Vendor Booth",
            booth_number="B-12",
            location="North hall",
            status="published",
        ),
        "admin@example.com",
    )
    configure_vendor_hall(db, event.id, VendorHallEventWrite(status="open"), "admin@example.com")
    booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
    assert booths is not None
    item = create_booth_inventory_item(
        db,
        booths[0].id,
        VendorHallInventoryItemWrite(
            item_name="Sleeper Sofa",
            model_number="SS-200",
            quantity_expected=2,
            unit_price="499.99",
            condition="new",
            available_for_sale=True,
            sell_to_buddys_price="399.99",
        ),
        db.scalar(select(User).where(User.email == "admin@example.com")),
    )
    assert item is not None
    return event.id, item.id


def test_store_loadout_module_and_permissions_are_registered() -> None:
    assert EVENT_MODULES["store-loadout"] == "Store loadout"
    assert EVENT_MODULES["event-settlement"] == "Event settlement and reconciliation"
    for permission in (
        "store_loadout.read",
        "store_loadout.manage",
        "store_loadout.store.checkin",
        "store_loadout.schedule.manage",
        "store_loadout.export",
        "event_settlement.read",
        "event_settlement.manage",
        "event_settlement.export",
    ):
        assert permission in CORE_PERMISSION_DEFINITIONS
    assert {
        "store_loadout.read",
        "store_loadout.store.checkin",
    } <= set(CORE_ROLE_DEFINITIONS["FRANCHISE_OPERATOR"]["permissions"])
    assert {
        "store_loadout.read",
        "store_loadout.manage",
        "store_loadout.schedule.manage",
        "store_loadout.export",
        "event_settlement.read",
        "event_settlement.manage",
        "event_settlement.export",
    } <= set(CORE_ROLE_DEFINITIONS["PURCHASING"]["permissions"])
    assert {
        "event_settlement.read",
        "event_settlement.manage",
        "event_settlement.export",
    } <= set(CORE_ROLE_DEFINITIONS["RECONCILIATION"]["permissions"])


def test_store_loadout_assigns_vendor_hall_inventory_to_store() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)

        loadout = configure_store_loadout(
            db,
            event_id,
            StoreLoadoutEventWrite(
                status="open",
                default_loadout_zone="Dock A",
                venue_departure_notes="Use west exit.",
            ),
            "admin@example.com",
        )
        assert loadout is not None
        assert loadout.default_loadout_zone == "Dock A"

        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                pickup_priority=1,
                distance_miles="125.50",
                estimated_drive_minutes=140,
                loadout_zone="Dock B",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        assert assignment.store_number == "1001"
        assert assignment.entity_code == "ENT-1"
        assert assignment.item_count == 1
        assert assignment.items[0].item_name == "Sleeper Sofa"
        assert assignment.items[0].quantity_assigned == 1

        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        teamed = assign_store_loadout_team(
            db,
            assignment.id,
            StoreLoadoutTeamWrite(
                team_name="Dock Team Alpha",
                team_member_emails=["store1001@example.com"],
                team_lead_emails=["lead@example.com", "staff@example.com"],
            ),
            admin,
        )
        assert teamed is not None
        assert teamed.team_name == "Dock Team Alpha"
        assert teamed.team_lead_emails == ["lead@example.com", "staff@example.com"]

        summary = store_loadout_summary(db, event_id)
        assert summary is not None
        assert summary.assignment_total == 1
        assert summary.item_total == 1
        assert summary.not_started == 1


def test_store_loadout_assignment_carries_latest_vendor_checkin_notes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        inventory_item = db.get(event_management.VendorHallInventoryItem, inventory_item_id)
        assert inventory_item is not None

        db.add_all(
            [
                VendorHallItemCheckin(
                    inventory_item_id=inventory_item.id,
                    vendor_hall_booth_id=inventory_item.vendor_hall_booth_id,
                    status="damaged",
                    quantity_checked=1,
                    damage_notes="Older note",
                    checked_by="staff@example.com",
                    checked_at=datetime(2027, 5, 1, 13, tzinfo=UTC),
                ),
                VendorHallItemCheckin(
                    inventory_item_id=inventory_item.id,
                    vendor_hall_booth_id=inventory_item.vendor_hall_booth_id,
                    status="damaged",
                    quantity_checked=1,
                    exception_notes="Latest inspection note",
                    checked_by="staff@example.com",
                    checked_at=datetime(2027, 5, 1, 14, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )

        assert assignment is not None
        assert assignment.items[0].damage_notes == "Latest inspection note"


def test_store_loadout_rejects_assignment_quantity_over_source_quantity() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=2,
                    )
                ],
            ),
            "admin@example.com",
        )
        try:
            create_store_loadout_assignment(
                db,
                event_id,
                StoreLoadoutAssignmentWrite(
                    store_number="1001",
                    items=[
                        StoreLoadoutItemAssignmentWrite(
                            vendor_hall_inventory_item_id=inventory_item_id,
                            quantity_assigned=1,
                        )
                    ],
                ),
                "admin@example.com",
            )
        except StoreLoadoutError as exc:
            assert "exceeds available" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected over-assignment rejection")


def test_store_loadout_mine_is_store_scoped() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        other_user = User(
            email="store9999@example.com",
            display_name="Other Store",
            password_hash="test",
            home_store_number="9999",
            is_active=True,
        )
        other_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add_all([store_user, other_user])
        db.commit()

        assert len(my_store_loadout_assignments(db, store_user)) == 1
        assert my_store_loadout_assignments(db, store_user)[0].store_number == "1001"
        assert my_store_loadout_assignments(db, other_user) == []


def test_store_loadout_mine_uses_loadout_window_not_main_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        configure_store_loadout(
            db,
            event_id,
            StoreLoadoutEventWrite(status="open"),
            "admin@example.com",
        )
        create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add(store_user)
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: store_user
        try:
            response = TestClient(app).get("/api/v1/store-loadout/mine")
            assert response.status_code == 200
            assert response.json()[0]["store_number"] == "1001"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_store_loadout_store_checkin_requires_open_loadout_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        configure_store_loadout(
            db,
            event_id,
            StoreLoadoutEventWrite(status="closed"),
            "admin@example.com",
        )
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add(store_user)
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: store_user
        try:
            response = TestClient(app).post(
                f"/api/v1/store-loadout/assignments/{assignment.id}/items/{assignment.items[0].id}/checkin",
                json={"status": "found", "quantity_found": 1},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Store loadout is not currently open"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_store_loadout_store_user_checks_in_item_and_marks_ready() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add(store_user)
        db.commit()

        checked = checkin_store_loadout_item(
            db,
            assignment.id,
            assignment.items[0].id,
            StoreLoadoutItemCheckinWrite(status="found", quantity_found=1),
            store_user,
        )
        assert checked is not None
        assert checked.status == "ready_for_final_review"
        assert checked.items[0].status == "found"
        assert checked.items[0].quantity_found == 1
        assert db.scalar(select(StoreLoadoutItemCheckin)) is not None

        ready = mark_store_loadout_assignment_ready(db, assignment.id, store_user)
        assert ready is not None
        assert ready.status == "ready_for_final_review"
        assert ready.final_review_requested_at is not None
        assert ready.final_review_requested_by == store_user.email
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        reviewed = complete_store_loadout_final_review(
            db,
            assignment.id,
            StoreLoadoutFinalReviewWrite(notes="Confirmed at dock."),
            admin,
        )
        assert reviewed is not None
        assert reviewed.final_review_completed_at is not None
        assert reviewed.final_review_completed_by == admin.email
        assert reviewed.final_review_notes == "Confirmed at dock."

        summary = store_loadout_summary(db, event_id)
        assert summary is not None
        assert summary.ready_for_final_review == 1
        assert summary.items_found == 1


def test_store_loadout_checkin_detects_exceptions_and_blocks_wrong_store() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        other_user = User(
            email="store9999@example.com",
            display_name="Other Store",
            password_hash="test",
            home_store_number="9999",
            is_active=True,
        )
        other_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add_all([store_user, other_user])
        db.commit()

        try:
            checkin_store_loadout_item(
                db,
                assignment.id,
                assignment.items[0].id,
                StoreLoadoutItemCheckinWrite(status="found", quantity_found=1),
                other_user,
            )
        except StoreLoadoutAccessError as exc:
            assert "outside" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected wrong-store check-in to be blocked")

        checked = checkin_store_loadout_item(
            db,
            assignment.id,
            assignment.items[0].id,
            StoreLoadoutItemCheckinWrite(
                status="found",
                quantity_found=0,
                missing_notes="Not at booth during pickup.",
            ),
            store_user,
        )
        assert checked is not None
        assert checked.status == "exceptions_present"
        assert checked.items[0].status == "quantity_mismatch"
        assert checked.exception_count == 1


def test_store_loadout_final_review_is_limited_to_manager_or_team_lead() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        team_lead = User(
            email="lead@example.com",
            display_name="Loadout Lead",
            password_hash="test",
            is_active=True,
        )
        team_lead.roles = [roles["FRANCHISE_OPERATOR"]]
        unrelated = User(
            email="other@example.com",
            display_name="Other Staff",
            password_hash="test",
            is_active=True,
        )
        unrelated.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add_all([store_user, team_lead, unrelated])
        db.commit()

        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        teamed = assign_store_loadout_team(
            db,
            assignment.id,
            StoreLoadoutTeamWrite(
                team_name="Dock Team Alpha",
                team_member_emails=["store1001@example.com"],
                team_lead_emails=["lead@example.com"],
            ),
            admin,
        )
        assert teamed is not None
        checked = checkin_store_loadout_item(
            db,
            assignment.id,
            assignment.items[0].id,
            StoreLoadoutItemCheckinWrite(status="found", quantity_found=1),
            store_user,
        )
        assert checked is not None
        ready = mark_store_loadout_assignment_ready(db, assignment.id, store_user)
        assert ready is not None

        try:
            complete_store_loadout_final_review(
                db,
                assignment.id,
                StoreLoadoutFinalReviewWrite(notes="Trying to approve."),
                unrelated,
            )
        except StoreLoadoutAccessError as exc:
            assert "team lead" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected unrelated staff final review to be blocked")

        reviewed = complete_store_loadout_final_review(
            db,
            assignment.id,
            StoreLoadoutFinalReviewWrite(notes="Lead verified dock loadout."),
            team_lead,
        )
        assert reviewed is not None
        assert reviewed.final_review_completed_by == "lead@example.com"
        assert reviewed.final_review_notes == "Lead verified dock loadout."

        export = store_loadout_export_rows(db, event_id, "master")
        assert export is not None
        headers, rows = export
        assert rows[0][headers.index("final_review_completed_by")] == "lead@example.com"
        assert rows[0][headers.index("final_review_notes")] == "Lead verified dock loadout."


def test_store_loadout_signs_releases_and_exports_assignment() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                loadout_zone="Dock C",
                recommended_departure_at=datetime(2027, 5, 3, 18, tzinfo=UTC),
                vehicle_labels=["Truck 1", "truck 1", "Truck 2"],
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        assert assignment.vehicle_labels == ["Truck 1", "Truck 2"]
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add(store_user)
        db.commit()

        checked = checkin_store_loadout_item(
            db,
            assignment.id,
            assignment.items[0].id,
            StoreLoadoutItemCheckinWrite(status="found", quantity_found=1),
            store_user,
        )
        assert checked is not None

        try:
            sign_store_loadout_assignment(
                db,
                assignment.id,
                StoreLoadoutSignoffWrite(
                    signer_name="Store Manager",
                    signer_email="store1001@example.com",
                    signature_text="Store Manager",
                ),
                store_user,
            )
        except StoreLoadoutError as exc:
            assert "final review" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected sign-off to require final review")

        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        reviewed = complete_store_loadout_final_review(
            db,
            assignment.id,
            StoreLoadoutFinalReviewWrite(notes="Ready for store signature."),
            admin,
        )
        assert reviewed is not None

        signed = sign_store_loadout_assignment(
            db,
            assignment.id,
            StoreLoadoutSignoffWrite(
                signer_name="Store Manager",
                signer_email="store1001@example.com",
                signature_text="Store Manager",
            ),
            store_user,
        )
        assert signed is not None
        assert signed.status == "signed_complete"
        assert signed.signed_at is not None
        assert signed.signed_by == "store1001@example.com"
        assert signed.items[0].status == "signed_off"
        signoff = latest_store_loadout_signoff(db, assignment.id)
        assert signoff is not None
        assert signoff.signer_name == "Store Manager"

        try:
            release_store_loadout_assignment(db, assignment.id, store_user)
        except StoreLoadoutAccessError as exc:
            assert "manager" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected store release to be blocked")

        for vehicle in ("Truck 1", "Truck 2"):
            for status in ("loading", "loaded", "departed"):
                released = update_store_loadout_vehicle_status(
                    db,
                    assignment.id,
                    vehicle,
                    StoreLoadoutVehicleStatusWrite(status=status),
                    admin,
                )
                assert released is not None
        assert released is not None
        assert released.status == "released_from_venue"
        assert released.released_at is not None

        export = store_loadout_export_rows(db, event_id, "master")
        assert export is not None
        headers, rows = export
        assert "store_number" in headers
        assert rows[0][headers.index("store_number")] == "1001"
        assert rows[0][headers.index("item_status")] == "signed_off"

        schedule_export = store_loadout_export_rows(db, event_id, "departure-schedule")
        assert schedule_export is not None
        assert schedule_export[1][0][schedule_export[0].index("loadout_zone")] == "Dock C"


def test_store_loadout_route_boundaries_for_release_and_exports() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = ensure_core_roles(db, ensure_core_permissions(db))
        _seed_foundation(db)
        event_id, inventory_item_id = _seed_vendor_hall_item(db)
        assignment = create_store_loadout_assignment(
            db,
            event_id,
            StoreLoadoutAssignmentWrite(
                store_number="1001",
                items=[
                    StoreLoadoutItemAssignmentWrite(
                        vendor_hall_inventory_item_id=inventory_item_id,
                        quantity_assigned=1,
                    )
                ],
            ),
            "admin@example.com",
        )
        assert assignment is not None
        store_user = User(
            email="store1001@example.com",
            display_name="Store 1001",
            password_hash="test",
            home_store_number="1001",
            is_active=True,
        )
        store_user.roles = [roles["FRANCHISE_OPERATOR"]]
        db.add(store_user)
        db.commit()
        checked = checkin_store_loadout_item(
            db,
            assignment.id,
            assignment.items[0].id,
            StoreLoadoutItemCheckinWrite(status="found", quantity_found=1),
            store_user,
        )
        assert checked is not None
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        reviewed = complete_store_loadout_final_review(
            db,
            assignment.id,
            StoreLoadoutFinalReviewWrite(notes=None),
            admin,
        )
        assert reviewed is not None
        signed = sign_store_loadout_assignment(
            db,
            assignment.id,
            StoreLoadoutSignoffWrite(
                signer_name="Store Manager",
                signer_email="store1001@example.com",
                signature_text="Store Manager",
            ),
            store_user,
        )
        assert signed is not None

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: store_user
        try:
            client = TestClient(app)
            response = client.post(f"/api/v1/store-loadout/assignments/{assignment.id}/release")
            assert response.status_code == 403
            response = client.get(f"/api/v1/store-loadout/events/{event_id}/exports/master")
            assert response.status_code == 403

            app.dependency_overrides[get_current_user] = lambda: admin
            response = client.post(f"/api/v1/store-loadout/assignments/{assignment.id}/release")
            assert response.status_code == 200
            assert response.json()["status"] == "released_from_venue"
            response = client.get(f"/api/v1/store-loadout/events/{event_id}/exports/master")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/csv")
            assert "Sleeper Sofa" in response.text
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
