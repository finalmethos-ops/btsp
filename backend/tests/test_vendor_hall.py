from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.vendor_hall import read_vendor_hall_directory
from app.auth.dependencies import get_current_user
from app.db.session import Base, get_db
from app.main import app
from app.models import (  # noqa: F401
    catalog,
    event_management,
    identity,
)
from app.models.catalog import CatalogVendor
from app.models.event_management import EventMembership, EventStaffTask, VendorHallBooth
from app.models.identity import User, user_vendor_access
from app.schemas.event_management import EVENT_MODULES, EventMembershipCreate, EventWrite
from app.schemas.event_vendor_booth import EventVendorBoothWrite
from app.schemas.vendor_hall import (
    VendorHallBoothCheckinWrite,
    VendorHallBoothMapPositionWrite,
    VendorHallBoothStaffAssignmentWrite,
    VendorHallEventWrite,
    VendorHallFloorMapWrite,
    VendorHallInventoryItemWrite,
    VendorHallItemCheckinWrite,
)
from app.services.admin_bootstrap_service import ensure_core_permissions, ensure_core_roles
from app.services.event_management_service import add_membership, create_event, publish_event
from app.services.event_vendor_booth_service import save_booth
from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS
from app.services.vendor_hall_service import (
    MAX_FLOOR_MAP_PAGES,
    VendorHallAccessError,
    VendorHallError,
    _pdf_text_positions,
    _user_is_booth_vendor,
    assign_booth_staff,
    attach_inventory_item_file,
    checkin_booth_inventory_item,
    complete_booth_checkin,
    configure_vendor_hall,
    create_booth_inventory_item,
    export_vendor_hall_report,
    import_booth_inventory_csv,
    import_vendor_hall_floor_map_pdf,
    inventory_item_attachment_content,
    list_booth_inventory,
    list_vendor_hall_booths,
    mark_booth_ready_for_inspection,
    my_vendor_hall_booths,
    remove_inventory_item_attachment,
    save_vendor_hall_floor_map,
    start_booth_checkin,
    submit_booth_inventory,
    sync_vendor_hall_booths,
    update_booth_inventory_item,
    update_booth_map_position,
    vendor_hall_floor_map_content,
    vendor_hall_floor_map_status,
    vendor_hall_summary,
)


def _event() -> EventWrite:
    return EventWrite(
        name="Vendor Hall 2027",
        slug="vendor-hall-2027",
        starts_at=datetime(2027, 5, 1, 12, tzinfo=UTC),
        ends_at=datetime(2027, 5, 3, 20, tzinfo=UTC),
        venue_name="Convention Center",
        address_line1="100 Show Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
    )


def _seed_vendor(db: Session) -> None:
    db.add(
        CatalogVendor(
            vendor_code="HALL",
            name="Hall Vendor",
            is_active=True,
            source_file="test",
        )
    )
    db.commit()


def _seed_roles(db: Session):
    permissions = ensure_core_permissions(db)
    return ensure_core_roles(db, permissions)


def test_floor_map_pdf_analysis_rejects_malformed_and_excessive_pages() -> None:
    with pytest.raises(VendorHallError, match="could not be read"):
        _pdf_text_positions(b"%PDF-not-a-real-document")

    pdf = BytesIO()
    canvas = Canvas(pdf, pagesize=letter, invariant=1)
    for page_number in range(MAX_FLOOR_MAP_PAGES + 1):
        canvas.drawString(50, 700, f"Floor plan page {page_number + 1}")
        canvas.showPage()
    canvas.save()

    with pytest.raises(VendorHallError, match=f"{MAX_FLOOR_MAP_PAGES} pages"):
        _pdf_text_positions(pdf.getvalue())


def test_vendor_hall_module_and_permissions_are_registered() -> None:
    assert EVENT_MODULES["vendor-hall-setup"] == "Vendor hall setup"
    for permission in (
        "vendor_hall.read",
        "vendor_hall.manage",
        "vendor_hall.vendor.manage",
        "vendor_hall.staff.checkin",
        "vendor_hall.export",
        "vendor_hall.map.manage",
    ):
        assert permission in CORE_PERMISSION_DEFINITIONS


def test_vendor_hall_booth_directory_uses_batched_queries() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        hall = configure_vendor_hall(
            db,
            event.id,
            VendorHallEventWrite(status="open"),
            "admin@example.com",
        )
        assert hall is not None
        db.add_all(
            VendorHallBooth(
                vendor_hall_event_id=hall.id,
                event_id=event.id,
                vendor_code="HALL",
                booth_number=f"B-{index:02d}",
                booth_name=f"Hall booth {index}",
            )
            for index in range(20)
        )
        db.commit()

        statements: list[str] = []

        def record_statement(*args) -> None:
            statements.append(args[2])

        sqlalchemy_event.listen(engine, "before_cursor_execute", record_statement)
        try:
            booths = list_vendor_hall_booths(db, event.id)
        finally:
            sqlalchemy_event.remove(engine, "before_cursor_execute", record_statement)

        assert booths is not None
        assert len(booths) == 20
        assert len(statements) <= 6


def test_vendor_hall_syncs_event_booths_and_scopes_vendor_access() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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

        hall = configure_vendor_hall(
            db,
            event.id,
            VendorHallEventWrite(status="open", require_staff_checkin=True),
            "admin@example.com",
        )
        assert hall is not None
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        assert len(booths) == 1
        assert booths[0].vendor_code == "HALL"
        assert booths[0].booth_number == "B-12"
        assert booths[0].status == "draft"

        summary = vendor_hall_summary(db, event.id)
        assert summary is not None
        assert summary.booth_total == 1
        assert summary.vendors_not_submitted[0].vendor_code == "HALL"

        vendor_user = db.scalar(select(User).where(User.email == "vendor@example.com"))
        assert vendor_user is not None
        my_booths = my_vendor_hall_booths(db, vendor_user)
        assert len(my_booths) == 1
        assert my_booths[0].booth_name == "Hall Vendor Booth"


def test_multi_vendor_representative_appears_at_and_can_access_each_booth() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_vendor(db)
        db.add(
            CatalogVendor(
                vendor_code="SECOND",
                name="Second Vendor",
                is_active=True,
                source_file="test",
            )
        )
        db.commit()
        event = create_event(
            db,
            _event().model_copy(
                update={
                    "starts_at": datetime(2020, 1, 1, 12, tzinfo=UTC),
                    "ends_at": datetime(2030, 1, 1, 12, tzinfo=UTC),
                }
            ),
            "admin@example.com",
        )
        representative = User(
            email="multi-vendor@example.com",
            display_name="Multi Vendor Representative",
            password_hash="test",
            vendor_code="HALL",
            is_active=True,
        )
        db.add(representative)
        db.flush()
        db.execute(
            user_vendor_access.insert().values(
                user_id=representative.id,
                vendor_code="SECOND",
            )
        )
        db.commit()
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email=representative.email,
                display_name=representative.display_name,
                membership_type="vendor",
                vendor_codes=["HALL", "SECOND"],
            ),
        )
        for vendor_code, booth_number in (("HALL", "B-12"), ("SECOND", "B-13")):
            save_booth(
                db,
                event.id,
                EventVendorBoothWrite(
                    vendor_code=vendor_code,
                    booth_name=f"{vendor_code} booth",
                    booth_number=booth_number,
                    location="North hall",
                    status="published",
                ),
                "admin@example.com",
            )
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        publish_event(db, event.id, "admin@example.com")
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None and len(booths) == 2
        assert len(my_vendor_hall_booths(db, representative)) == 2
        assert all(_user_is_booth_vendor(db, representative, booth) for booth in booths)

        directory = read_vendor_hall_directory(event.id, db, representative)
        assert all(booth.attendees == ["Multi Vendor Representative"] for booth in directory.booths)


def test_vendor_hall_directory_message_requires_event_membership() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_vendor(db)
        event = create_event(
            db,
            _event().model_copy(
                update={
                    "starts_at": datetime(2020, 1, 1, 12, tzinfo=UTC),
                    "ends_at": datetime(2030, 1, 1, 12, tzinfo=UTC),
                }
            ),
            "admin@example.com",
        )
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        non_member = User(
            email="visitor@example.com",
            display_name="Unassigned Visitor",
            password_hash="test",
            is_active=True,
        )
        db.add(non_member)
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: non_member
        try:
            client = TestClient(app)
            response = client.post(
                f"/api/v1/vendor-hall/events/{event.id}/directory/booths/{booths[0].id}/messages",
                json={"subject": "Question", "body": "Can we visit this booth?"},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Event access is not currently available"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_vendor_hall_rejects_sub_event_from_another_event() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = create_event(db, _event(), "admin@example.com")
        second = create_event(
            db,
            _event().model_copy(update={"name": "Other Vendor Hall", "slug": "other-vendor-hall"}),
            "admin@example.com",
        )
        db.add(
            event_management.ManagedSubEvent(
                event_id=second.id,
                name="Other floor",
                starts_at=datetime(2027, 5, 1, 14, tzinfo=UTC),
                ends_at=datetime(2027, 5, 1, 18, tzinfo=UTC),
                location="Other hall",
            )
        )
        db.commit()
        sub_event = db.scalar(
            select(event_management.ManagedSubEvent).where(
                event_management.ManagedSubEvent.event_id == second.id
            )
        )
        assert sub_event is not None

        try:
            configure_vendor_hall(
                db,
                first.id,
                VendorHallEventWrite(sub_event_id=sub_event.id),
                "admin@example.com",
            )
        except ValueError as exc:
            assert "Sub-event does not belong" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected cross-event sub-event rejection")


def test_vendor_hall_inventory_submission_and_staff_checkin() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        booth = booths[0]

        vendor_user = db.scalar(select(User).where(User.email == "vendor@example.com"))
        assert vendor_user is not None
        vendor_user.roles = [roles["VENDOR"]]
        staff_user = User(
            email="staff@example.com",
            display_name="Staff Checker",
            password_hash="test",
            is_active=True,
        )
        staff_user.roles = [roles["PURCHASING"]]
        db.add(staff_user)
        db.commit()
        staff_membership = EventMembership(
            event_id=event.id,
            user_id=staff_user.id,
            membership_type="staff",
            is_active=True,
        )
        db.add(staff_membership)
        db.commit()
        assign_booth_staff(
            db,
            event.id,
            booth.id,
            VendorHallBoothStaffAssignmentWrite(membership_id=staff_membership.id),
            staff_user,
        )

        item = create_booth_inventory_item(
            db,
            booth.id,
            VendorHallInventoryItemWrite(
                item_name="Motion Sofa",
                model_number="MS-100",
                serial_number="SER-1",
                quantity_expected=1,
                unit_price="399.99",
                condition="new",
                available_for_sale=True,
                sell_to_buddys_price="299.99",
            ),
            vendor_user,
        )
        assert item is not None
        assert item.vendor_code == "HALL"
        assert item.available_for_sale is True

        submitted = submit_booth_inventory(db, booth.id, vendor_user)
        assert submitted is not None
        assert submitted.status == "inventory_submitted"

        # Vendors must classify every unit before requesting staff inspection.
        update_booth_inventory_item(
            db,
            booth.id,
            item.id,
            VendorHallInventoryItemWrite(
                item_name=item.item_name,
                model_number=item.model_number,
                serial_number=item.serial_number,
                quantity_expected=item.quantity_expected,
                condition=item.condition,
                status="checked_in",
                available_for_sale=item.available_for_sale,
                sell_to_buddys_price=item.sell_to_buddys_price,
            ),
            vendor_user,
        )

        ready = mark_booth_ready_for_inspection(db, booth.id, vendor_user)
        assert ready is not None
        assert ready.status == "ready_for_inspection"
        inspection_task = db.scalar(
            select(EventStaffTask).where(EventStaffTask.vendor_hall_booth_id == booth.id)
        )
        assert inspection_task is not None
        assert inspection_task.assigned_membership_id == staff_membership.id

        started = start_booth_checkin(
            db, booth.id, VendorHallBoothCheckinWrite(notes="Opening scan"), staff_user
        )
        assert started is not None
        assert started.items_expected == 1
        db.refresh(inspection_task)
        assert inspection_task.status == "in_progress"

        checked = checkin_booth_inventory_item(
            db,
            booth.id,
            item.id,
            VendorHallItemCheckinWrite(
                status="damaged",
                quantity_checked=1,
                condition="damaged",
                damage_notes="Scratch on left arm",
                staff_notes="Photo captured on device",
            ),
            staff_user,
        )
        assert checked is not None
        assert checked.status == "damaged"
        refreshed_inventory = list_booth_inventory(db, booth.id, staff_user)
        assert refreshed_inventory is not None
        assert refreshed_inventory[0].validated is True

        completed = complete_booth_checkin(
            db, booth.id, VendorHallBoothCheckinWrite(notes="Needs vendor review"), staff_user
        )
        assert completed is not None
        assert completed.status == "exceptions_present"
        assert completed.exceptions_count == 1
        db.refresh(inspection_task)
        assert inspection_task.status == "blocked"

        summary = vendor_hall_summary(db, event.id)
        assert summary is not None
        assert summary.exceptions_present == 1

        available_export = export_vendor_hall_report(db, event.id, "available-for-sale")
        assert available_export is not None
        assert available_export[0].endswith("available-for-sale.csv")
        assert "Motion Sofa" in available_export[1]
        assert "299.99" in available_export[1]

        damaged_export = export_vendor_hall_report(db, event.id, "damaged-items")
        assert damaged_export is not None
        assert "Scratch on left arm" in damaged_export[1] or "Motion Sofa" in damaged_export[1]

        staff_log = export_vendor_hall_report(db, event.id, "staff-checkin-log")
        assert staff_log is not None
        assert "item_checkin" in staff_log[1]
        assert "staff@example.com" in staff_log[1]


def test_vendor_hall_inventory_is_vendor_scoped() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        booth = booths[0]

        other_vendor = User(
            email="other-vendor@example.com",
            display_name="Other Vendor",
            password_hash="test",
            vendor_code="OTHER",
            is_active=True,
        )
        other_vendor.roles = [roles["VENDOR"]]
        db.add(other_vendor)
        db.commit()

        try:
            create_booth_inventory_item(
                db,
                booth.id,
                VendorHallInventoryItemWrite(item_name="Unauthorized item"),
                other_vendor,
            )
        except VendorHallAccessError as exc:
            assert "cannot manage inventory" in str(exc)
        else:  # pragma: no cover - defensive branch
            raise AssertionError("Expected vendor booth scope enforcement")


def test_vendor_hall_vendor_inventory_write_requires_event_window() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
        event = create_event(
            db,
            EventWrite(
                name="Expired Vendor Hall",
                slug="expired-vendor-hall",
                starts_at=datetime(2020, 5, 1, 12, tzinfo=UTC),
                ends_at=datetime(2020, 5, 3, 20, tzinfo=UTC),
                venue_name="Convention Center",
                address_line1="100 Show Way",
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
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        vendor_user = db.scalar(select(User).where(User.email == "vendor@example.com"))
        assert vendor_user is not None
        vendor_user.roles = [roles["VENDOR"]]
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: vendor_user
        try:
            response = TestClient(app).post(
                f"/api/v1/vendor-hall/booths/{booths[0].id}/inventory",
                json={
                    "item_name": "Expired write attempt",
                    "quantity_expected": 1,
                    "currency": "USD",
                    "condition": "new",
                    "status": "expected",
                    "available_for_sale": False,
                },
            )
            assert response.status_code == 403
            assert response.json()["detail"] == ("Event access is outside the scheduled window")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def test_vendor_hall_imports_inventory_and_uploads_item_attachment() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="vendor@example.com",
                display_name="Hall Vendor",
                password="Vendor-Event-Password!",
                membership_type="vendor",
                vendor_code="HALL",
            ),
        )
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        booth = booths[0]

        vendor_user = db.scalar(select(User).where(User.email == "vendor@example.com"))
        assert vendor_user is not None
        vendor_user.roles = [roles["VENDOR"]]
        db.commit()

        inventory_import = import_booth_inventory_csv(
            db,
            booth.id,
            "booth.csv",
            "text/csv",
            (
                b"item_name,model_number,quantity_expected,unit_price,"
                b"condition,available_for_sale,sell_to_buddys_price\n"
                b"Sleeper Sofa,SS-200,2,499.99,new,yes,399.99\n"
                b",BROKEN,1,10.00,used,no,\n"
            ),
            vendor_user,
        )
        assert inventory_import is not None
        assert inventory_import.row_count == 2
        assert inventory_import.accepted_count == 1
        assert inventory_import.rejected_count == 1
        assert inventory_import.status == "completed_with_errors"

        with pytest.raises(VendorHallError, match="UTF-8"):
            import_booth_inventory_csv(
                db,
                booth.id,
                "invalid.csv",
                "text/csv",
                b"item_name\n\xff\n",
                vendor_user,
            )
        with pytest.raises(VendorHallError, match="must be a CSV"):
            import_booth_inventory_csv(
                db,
                booth.id,
                "inventory.txt",
                "text/plain",
                b"item_name\nSleeper Sofa\n",
                vendor_user,
            )
        oversized_rows = b"item_name\n" + (b"Item\n" * 10_001)
        with pytest.raises(VendorHallError, match="10,000 rows"):
            import_booth_inventory_csv(
                db,
                booth.id,
                "too-many-rows.csv",
                "text/csv",
                oversized_rows,
                vendor_user,
            )

        item = db.scalar(
            select(event_management.VendorHallInventoryItem).where(
                event_management.VendorHallInventoryItem.vendor_hall_booth_id == booth.id
            )
        )
        assert item is not None
        assert item.item_name == "Sleeper Sofa"
        attachment = attach_inventory_item_file(
            db,
            booth.id,
            item.id,
            "photo",
            "sleeper.webp",
            "image/webp",
            b"RIFF\x04\x00\x00\x00WEBP",
            vendor_user,
        )
        assert attachment is not None
        assert attachment.attachment_type == "photo"
        assert attachment.filename == "sleeper.webp"
        refreshed_items = list_booth_inventory(db, booth.id, vendor_user)
        assert refreshed_items is not None
        assert [file.id for file in refreshed_items[0].attachments] == [attachment.id]
        assert inventory_item_attachment_content(
            db, booth.id, item.id, attachment.id, vendor_user
        ) == ("sleeper.webp", "image/webp", b"RIFF\x04\x00\x00\x00WEBP")

        unauthorized = User(
            email="unassigned@example.com",
            display_name="Unassigned User",
            password_hash="test",
            is_active=True,
        )
        db.add(unauthorized)
        db.commit()
        with pytest.raises(VendorHallAccessError, match="do not have access"):
            inventory_item_attachment_content(db, booth.id, item.id, attachment.id, unauthorized)
        assert remove_inventory_item_attachment(db, booth.id, item.id, attachment.id, vendor_user)
        refreshed_items = list_booth_inventory(db, booth.id, vendor_user)
        assert refreshed_items is not None
        assert refreshed_items[0].attachments == []

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["item_name", "model_number", "quantity_expected", "condition"])
        worksheet.append(["Excel Table", "XL-100", 3, "new"])
        workbook_content = BytesIO()
        workbook.save(workbook_content)
        excel_import = import_booth_inventory_csv(
            db,
            booth.id,
            "booth.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            workbook_content.getvalue(),
            vendor_user,
        )
        assert excel_import is not None
        assert excel_import.row_count == 1
        assert excel_import.accepted_count == 1
        assert excel_import.rejected_count == 0
        deletion_audit = db.scalar(
            select(event_management.VendorHallAuditLog).where(
                event_management.VendorHallAuditLog.action
                == "vendor_hall.inventory_item.attachment_deleted"
            )
        )
        assert deletion_audit is not None
        assert deletion_audit.payload["attachment_id"] == attachment.id


def test_vendor_hall_floor_map_status_includes_booth_positions() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
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
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert booths is not None
        booth = booths[0]
        admin_user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash="test",
            is_active=True,
        )
        admin_user.roles = [roles["ADMIN"]]
        db.add(admin_user)
        db.commit()

        floor_map = save_vendor_hall_floor_map(
            db,
            event.id,
            VendorHallFloorMapWrite(
                name="Main hall",
                layout_json={"zones": ["north", "south"]},
            ),
            admin_user,
        )
        assert floor_map is not None
        assert floor_map.name == "Main hall"

        positioned = update_booth_map_position(
            db,
            event.id,
            booth.id,
            VendorHallBoothMapPositionWrite(
                floor_map_zone="north",
                map_x="10.5",
                map_y="20.25",
                map_width="8",
                map_height="6",
            ),
            admin_user,
        )
        assert positioned is not None
        assert positioned.floor_map_zone == "north"

        status = vendor_hall_floor_map_status(db, event.id)
        assert status is not None
        assert status.floor_map is not None
        assert status.floor_map.layout_json == {"zones": ["north", "south"]}
        assert status.booths[0].map_x is not None

        pdf = BytesIO()
        canvas = Canvas(pdf, pagesize=letter, invariant=1)
        canvas.drawString(150, 600, "B-120")
        canvas.showPage()
        canvas.drawString(150, 600, "B-12")
        canvas.save()
        imported = import_vendor_hall_floor_map_pdf(
            db,
            event.id,
            "Imported main hall",
            "main-hall.pdf",
            "application/pdf",
            pdf.getvalue(),
            admin_user,
        )
        assert imported is not None and imported.has_image is True
        assert imported.layout_json["page_count"] == 2
        assert imported.layout_json["scanned_page"] == 2
        assert imported.layout_json["detected_booth_count"] == 1
        assert imported.layout_json["unmatched_booth_count"] == 0
        assert imported.layout_json["analysis_version"] == "vendor-hall-map-v2"
        assert imported.layout_json["fallback_geometry_count"] == 1
        assert imported.layout_json["review_required"] is True
        status = vendor_hall_floor_map_status(db, event.id)
        assert status is not None
        assert 49 < float(status.booths[0].map_x or 0) < 51
        assert status.floor_map.layout_json["crop_box"]
        assert 30 < float(status.booths[0].map_y or 0) < 45
        source = vendor_hall_floor_map_content(db, event.id)
        assert source is not None
        assert source[0] == "main-hall.pdf"
        assert source[1] == "application/pdf"
        assert source[2].startswith(b"%PDF")


def test_vendor_hall_booth_sync_rescans_existing_floor_map_pdf() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        roles = _seed_roles(db)
        _seed_vendor(db)
        event = create_event(db, _event(), "admin@example.com")
        configure_vendor_hall(
            db, event.id, VendorHallEventWrite(status="open"), "admin@example.com"
        )
        admin_user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash="test",
            is_active=True,
        )
        admin_user.roles = [roles["ADMIN"]]
        db.add(admin_user)
        db.commit()

        pdf = BytesIO()
        canvas = Canvas(pdf, pagesize=letter, invariant=1)
        canvas.drawString(150, 600, "B-12")
        canvas.save()
        imported = import_vendor_hall_floor_map_pdf(
            db,
            event.id,
            "Imported before booths",
            "before-booths.pdf",
            "application/pdf",
            pdf.getvalue(),
            admin_user,
        )
        assert imported is not None
        assert imported.layout_json["detected_booth_count"] == 0
        assert imported.layout_json["unmatched_booth_count"] == 0

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
        booths = sync_vendor_hall_booths(db, event.id, "admin@example.com")

        assert booths is not None
        assert 49 < float(booths[0].map_x or 0) < 51
        status = vendor_hall_floor_map_status(db, event.id)
        assert status is not None and status.floor_map is not None
        assert status.floor_map.layout_json["detected_booth_count"] == 1
        assert status.floor_map.layout_json["unmatched_booth_count"] == 0
        assert status.floor_map.layout_json["analysis_version"] == "vendor-hall-map-v2"
        adjusted = update_booth_map_position(
            db,
            event.id,
            booths[0].id,
            VendorHallBoothMapPositionWrite(
                floor_map_zone="manual",
                map_x="44",
                map_y="45",
                map_width="12.5",
                map_height="9.25",
            ),
            admin_user,
        )
        assert adjusted is not None and adjusted.map_manually_adjusted is True
        rescanned = sync_vendor_hall_booths(db, event.id, "admin@example.com")
        assert rescanned is not None
        assert float(rescanned[0].map_width or 0) == 12.5
        assert float(rescanned[0].map_height or 0) == 9.25
