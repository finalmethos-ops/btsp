from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_management import (
    EventAnnouncement,
    EventCalendarEntry,
    EventMembership,
    EventProductSlide,
    EventSettlementEvent,
    EventVendorBooth,
    ManagedEvent,
    ManagedSubEvent,
    StoreLoadoutAssignment,
    StoreLoadoutEvent,
    StoreLoadoutItem,
    VendorHallBooth,
    VendorHallEvent,
    VendorHallInventoryItem,
)
from app.models.identity import User
from app.models.store import Store
from app.services.admin_bootstrap_service import ensure_core_permissions, ensure_core_roles

DEMO_VENDOR_CODE = "PERF-001"
DEMO_EVENT_SLUG = "btsp-uat-demo-2026"
DEMO_PRODUCTS = (
    ("DEMO-TV-55", 'Demo 55" Television', Decimal("349.00")),
    ("DEMO-SOFA-01", "Demo Living Room Sofa", Decimal("499.00")),
    ("DEMO-WASHER-01", "Demo Washer", Decimal("399.00")),
)
DEMO_PRODUCT_DETAILS = {
    "DEMO-TV-55": (
        "Electronics",
        "Televisions",
        "A feature-rich 55-inch television designed for a vivid home entertainment experience.",
    ),
    "DEMO-SOFA-01": (
        "Furniture",
        "Living Room",
        "A comfortable, durable sofa with versatile styling for everyday living spaces.",
    ),
    "DEMO-WASHER-01": (
        "Appliances",
        "Laundry",
        "A dependable high-capacity washer with convenient cycles for everyday laundry.",
    ),
}


@dataclass(frozen=True)
class DemoAccount:
    email: str
    display_name: str
    role_code: str
    attendee_category: str
    vendor_code: str | None = None
    entity_code: str | None = None
    home_store_number: str | None = None
    region_code: str | None = None


DEMO_ACCOUNTS = (
    DemoAccount(
        email="admin.demo@btsp.local",
        display_name="Event Administrator Demo",
        role_code="ADMIN",
        attendee_category="admin",
    ),
    DemoAccount(
        email="vendor.demo@btsp.local",
        display_name="Vendor Demo - PERF-001",
        role_code="VENDOR",
        attendee_category="vendor",
        vendor_code=DEMO_VENDOR_CODE,
    ),
    DemoAccount(
        email="franchise.demo@btsp.local",
        display_name="Franchise Representative Demo",
        role_code="FRANCHISE_OPERATOR",
        attendee_category="franchise_representative",
        entity_code="BEBE",
        home_store_number="0002",
        region_code="9200",
    ),
    DemoAccount(
        email="executive.demo@btsp.local",
        display_name="Executive Demo",
        role_code="EXECUTIVE",
        attendee_category="executive",
    ),
    DemoAccount(
        email="staff.demo@btsp.local",
        display_name="Event Staff Demo",
        role_code="EVENT_STAFF",
        attendee_category="staff",
    ),
)


def _ensure_demo_vendor(db: Session) -> CatalogVendor:
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == DEMO_VENDOR_CODE))
    if vendor is None:
        vendor = CatalogVendor(
            vendor_code=DEMO_VENDOR_CODE,
            name="BTSP Demo Vendor",
            is_active=True,
            source_file="event-demo-seed",
        )
        db.add(vendor)
        db.flush()
    else:
        vendor.is_active = True
    for product_code, name, unit_price in DEMO_PRODUCTS:
        department, category, _ = DEMO_PRODUCT_DETAILS[product_code]
        product = db.scalar(
            select(CatalogProduct).where(CatalogProduct.product_code == product_code)
        )
        if product is None:
            db.add(
                CatalogProduct(
                    product_code=product_code,
                    model_number=product_code,
                    vendor_code=DEMO_VENDOR_CODE,
                    name=name,
                    department=department,
                    product_category_code=category,
                    unit_price=unit_price,
                    currency="USD",
                    minimum_order_quantity=1,
                    is_available=True,
                    is_active=True,
                    source_file="event-demo-seed",
                )
            )
        else:
            product.department = department
            product.product_category_code = category
    db.execute(
        update(CatalogProduct)
        .where(CatalogProduct.vendor_code == DEMO_VENDOR_CODE)
        .values(is_active=True, is_available=True)
    )
    return vendor


def _ensure_demo_store(db: Session) -> Store:
    store = db.scalar(select(Store).where(Store.store_number == "0002"))
    if store is None:
        store = Store(
            store_number="0002",
            name="BTSP Demo Store 0002",
            region_code="9200",
            entity_code="BEBE",
            purchasing_program="BPP",
            city="Orlando",
            state_code="FL",
            timezone="America/New_York",
            is_ordering_enabled=True,
            is_active=True,
            source_system="event-demo-seed",
        )
        db.add(store)
        db.flush()
    else:
        store.entity_code = "BEBE"
        store.region_code = "9200"
        store.is_ordering_enabled = True
        store.is_active = True
    return store


def seed_event_demo_accounts(db: Session, password: str) -> list[DemoAccount]:
    if len(password) < 12:
        raise ValueError("Demo password must contain at least 12 characters")
    permissions = ensure_core_permissions(db)
    roles = ensure_core_roles(db, permissions)
    _ensure_demo_vendor(db)
    _ensure_demo_store(db)
    password_hash = hash_password(password)
    for account in DEMO_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == account.email))
        if user is None:
            user = User(
                email=account.email,
                display_name=account.display_name,
                password_hash=password_hash,
                is_active=True,
            )
            db.add(user)
        user.display_name = account.display_name
        user.password_hash = password_hash
        user.vendor_code = account.vendor_code
        user.home_store_number = account.home_store_number
        user.region_code = account.region_code
        user.is_active = True
        user.roles = [roles[account.role_code]]
    db.commit()
    return list(DEMO_ACCOUNTS)


def _ensure_demo_operations(db: Session, event: ManagedEvent, actor: str) -> None:
    sub_events = {
        item.name: item
        for item in db.scalars(
            select(ManagedSubEvent).where(ManagedSubEvent.event_id == event.id)
        ).all()
    }
    audiences = ["admin", "executive", "franchise_representative", "staff", "vendor"]
    announcement = db.scalar(
        select(EventAnnouncement).where(
            EventAnnouncement.event_id == event.id,
            EventAnnouncement.title == "Welcome to the BTSP event experience",
        )
    )
    if announcement is None:
        db.add(
            EventAnnouncement(
                event_id=event.id,
                sub_event_id=None,
                title="Welcome to the BTSP event experience",
                body=(
                    "Your live schedule, assigned event tools, and attendee pass are "
                    "available from this event home."
                ),
                severity="info",
                visibility_categories=audiences,
                publishes_at=event.starts_at,
                expires_at=event.ends_at,
                is_active=True,
                created_by=actor,
            )
        )
    welcome = db.scalar(
        select(EventCalendarEntry).where(
            EventCalendarEntry.event_id == event.id,
            EventCalendarEntry.entry_type == "text",
            EventCalendarEntry.title == "Welcome and event registration",
        )
    )
    if welcome is None:
        db.add(
            EventCalendarEntry(
                event_id=event.id,
                sub_event_id=None,
                entry_type="text",
                title="Welcome and event registration",
                description=(
                    "Pick up credentials and review the show schedule before sessions begin."
                ),
                starts_at=event.starts_at,
                ends_at=event.starts_at + timedelta(hours=1),
                location="Registration Desk",
                visibility_categories=audiences,
                is_active=True,
                created_by=actor,
            )
        )
    for sub_event in sub_events.values():
        existing_entry = db.scalar(
            select(EventCalendarEntry).where(
                EventCalendarEntry.event_id == event.id,
                EventCalendarEntry.sub_event_id == sub_event.id,
            )
        )
        if existing_entry is None:
            db.add(
                EventCalendarEntry(
                    event_id=event.id,
                    sub_event_id=sub_event.id,
                    entry_type="sub_event",
                    title=sub_event.name,
                    description=sub_event.description,
                    starts_at=sub_event.starts_at,
                    ends_at=sub_event.ends_at,
                    location=sub_event.location,
                    visibility_categories=audiences,
                    is_active=True,
                    created_by=actor,
                )
            )
    setup = sub_events.get("Vendor Hall Setup")
    hall = db.scalar(select(VendorHallEvent).where(VendorHallEvent.event_id == event.id))
    if hall is None:
        hall = VendorHallEvent(
            event_id=event.id,
            sub_event_id=setup.id if setup else None,
            status="open",
            opens_at=setup.starts_at if setup else event.starts_at,
            vendor_submission_deadline=setup.starts_at if setup else event.starts_at,
            staff_checkin_opens_at=setup.starts_at if setup else event.starts_at,
            staff_checkin_deadline=setup.ends_at if setup else event.ends_at,
            allow_vendor_edits_after_submission=True,
            require_staff_checkin=True,
            created_by=actor,
        )
        db.add(hall)
        db.flush()
    event_booth = db.scalar(
        select(EventVendorBooth).where(
            EventVendorBooth.event_id == event.id,
            EventVendorBooth.vendor_code == DEMO_VENDOR_CODE,
        )
    )
    hall_booth = db.scalar(
        select(VendorHallBooth).where(
            VendorHallBooth.event_id == event.id,
            VendorHallBooth.vendor_code == DEMO_VENDOR_CODE,
        )
    )
    if hall_booth is None and event_booth is not None:
        hall_booth = VendorHallBooth(
            vendor_hall_event_id=hall.id,
            event_vendor_booth_id=event_booth.id,
            event_id=event.id,
            vendor_code=DEMO_VENDOR_CODE,
            booth_number=event_booth.booth_number or "D-101",
            booth_name=event_booth.booth_name,
            floor_map_zone="Demo Vendor Hall",
            map_x=Decimal("12"),
            map_y=Decimal("18"),
            map_width=Decimal("24"),
            map_height=Decimal("18"),
            status="draft",
        )
        db.add(hall_booth)
        db.flush()
    if hall_booth is not None and hall_booth.assigned_staff_membership_id is None:
        staff_membership = db.scalar(
            select(EventMembership).where(
                EventMembership.event_id == event.id,
                EventMembership.membership_type == "staff",
                EventMembership.is_active.is_(True),
            )
        )
        if staff_membership is not None:
            hall_booth.assigned_staff_membership_id = staff_membership.id
    inventory: list[VendorHallInventoryItem] = []
    if hall_booth is not None:
        existing_items = {
            item.model_number: item
            for item in db.scalars(
                select(VendorHallInventoryItem).where(
                    VendorHallInventoryItem.vendor_hall_booth_id == hall_booth.id
                )
            ).all()
        }
        products = db.scalars(
            select(CatalogProduct).where(
                CatalogProduct.product_code.in_([item[0] for item in DEMO_PRODUCTS])
            )
        ).all()
        for index, product in enumerate(products):
            item = existing_items.get(product.model_number)
            if item is None:
                item = VendorHallInventoryItem(
                    vendor_hall_booth_id=hall_booth.id,
                    event_id=event.id,
                    vendor_code=DEMO_VENDOR_CODE,
                    source="demo_seed",
                    model_number=product.model_number,
                    serial_number=f"UAT-{index + 1:03d}",
                    item_name=product.name,
                    description=DEMO_PRODUCT_DETAILS[product.product_code][2],
                    quantity_expected=2 if index == 0 else 1,
                    unit_price=product.unit_price,
                    currency=product.currency,
                    condition="new",
                    status="expected",
                    available_for_sale=True,
                    sell_to_buddys_price=product.unit_price,
                    vendor_notes="Demo inventory ready for vendor preliminary review.",
                    created_by="vendor.demo@btsp.local",
                )
                db.add(item)
                db.flush()
            inventory.append(item)
    loadout = db.scalar(select(StoreLoadoutEvent).where(StoreLoadoutEvent.event_id == event.id))
    if loadout is None:
        loadout_sub_event = sub_events.get("Store Loadout and Closeout")
        loadout = StoreLoadoutEvent(
            event_id=event.id,
            status="open",
            opens_at=loadout_sub_event.starts_at if loadout_sub_event else None,
            loadout_deadline=loadout_sub_event.ends_at if loadout_sub_event else None,
            default_loadout_zone="Zone A",
            venue_departure_notes="Complete item checks and request staff final review.",
            created_by=actor,
        )
        db.add(loadout)
        db.flush()
    assignment = db.scalar(
        select(StoreLoadoutAssignment).where(
            StoreLoadoutAssignment.event_id == event.id,
            StoreLoadoutAssignment.store_number == "0002",
        )
    )
    if assignment is None and inventory:
        assignment = StoreLoadoutAssignment(
            store_loadout_event_id=loadout.id,
            event_id=event.id,
            store_number="0002",
            entity_code="BEBE",
            status="not_started",
            pickup_priority=10,
            loadout_zone="Zone A",
            distance_miles=Decimal("18.5"),
            estimated_drive_minutes=30,
            notes="Demo store loadout assignment.",
            team_name="Demo Loadout Team",
            team_member_emails=["franchise.demo@btsp.local"],
            team_lead_emails=["staff.demo@btsp.local"],
            assigned_by=actor,
        )
        db.add(assignment)
        db.flush()
        for item in inventory:
            db.add(
                StoreLoadoutItem(
                    assignment_id=assignment.id,
                    event_id=event.id,
                    vendor_hall_booth_id=hall_booth.id,
                    vendor_hall_inventory_item_id=item.id,
                    vendor_code=item.vendor_code,
                    booth_number=hall_booth.booth_number,
                    item_name=item.item_name,
                    model_number=item.model_number,
                    serial_number=item.serial_number,
                    quantity_assigned=1,
                    condition=item.condition,
                    status="assigned",
                    notes="Locate, inspect, and prepare for final review.",
                )
            )
    settlement = db.scalar(
        select(EventSettlementEvent).where(EventSettlementEvent.event_id == event.id)
    )
    if settlement is None:
        db.add(
            EventSettlementEvent(
                event_id=event.id,
                status="collecting_evidence",
                notes="UAT settlement workspace awaiting lifecycle completion.",
                created_by=actor,
            )
        )


def seed_event_demo_event(db: Session, password: str) -> ManagedEvent:
    seed_event_demo_accounts(db, password)
    existing = db.scalar(select(ManagedEvent).where(ManagedEvent.slug == DEMO_EVENT_SLUG))
    if existing is not None:
        _ensure_demo_operations(db, existing, "admin.demo@btsp.local")
        db.commit()
        db.refresh(existing)
        return existing
    admin_email = "admin.demo@btsp.local"
    event = ManagedEvent(
        slug=DEMO_EVENT_SLUG,
        name="BTSP Full Lifecycle UAT",
        description="Local mock event for end-to-end event platform validation.",
        status="published",
        starts_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
        ends_at=datetime(2026, 8, 13, 21, tzinfo=UTC),
        timezone="America/New_York",
        venue_name="BTSP Demo Convention Center",
        address_line1="100 Demo Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
        country_code="US",
        created_by=admin_email,
    )
    db.add(event)
    db.flush()
    sub_events = [
        ManagedSubEvent(
            event_id=event.id,
            name="Vendor Hall Setup",
            starts_at=datetime(2026, 8, 10, 13, tzinfo=UTC),
            ends_at=datetime(2026, 8, 10, 20, tzinfo=UTC),
            location="Vendor Hall",
            status="published",
            module_codes=[
                "check-in",
                "staff-tasks",
                "vendor-booths",
                "vendor-hall-setup",
                "vendor-hall-inventory",
            ],
        ),
        ManagedSubEvent(
            event_id=event.id,
            name="Live Buying Presentation",
            starts_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
            ends_at=datetime(2026, 8, 11, 18, tzinfo=UTC),
            location="Main Stage",
            status="published",
            module_codes=["live-display", "ordering", "polling", "product-slides"],
        ),
        ManagedSubEvent(
            event_id=event.id,
            name="Store Loadout and Closeout",
            starts_at=datetime(2026, 8, 12, 13, tzinfo=UTC),
            ends_at=datetime(2026, 8, 12, 20, tzinfo=UTC),
            location="Loading Zone",
            status="published",
            module_codes=["store-loadout", "event-settlement"],
        ),
        ManagedSubEvent(
            event_id=event.id,
            name="Vendor Buy Fair",
            starts_at=datetime(2026, 8, 13, 13, tzinfo=UTC),
            ends_at=datetime(2026, 8, 13, 19, tzinfo=UTC),
            location="Buying Hall",
            status="published",
            module_codes=["vendor-buy-fair"],
        ),
    ]
    db.add_all(sub_events)
    db.flush()
    users = {
        user.email: user
        for user in db.scalars(select(User).where(User.email.in_([a.email for a in DEMO_ACCOUNTS])))
    }
    for account in DEMO_ACCOUNTS:
        db.add(
            EventMembership(
                event_id=event.id,
                user_id=users[account.email].id,
                membership_type=account.attendee_category,
                vendor_code=account.vendor_code,
                entity_code=account.entity_code,
                module_codes=sorted({code for item in sub_events for code in item.module_codes}),
                task_scope="Full local UAT scope" if account.attendee_category == "staff" else None,
                is_active=True,
            )
        )
    db.add(
        EventVendorBooth(
            event_id=event.id,
            vendor_code=DEMO_VENDOR_CODE,
            booth_name="BTSP Demo Vendor",
            booth_number="D-101",
            location="Vendor Hall",
            description="Demo booth for Vendor Hall and ordering validation.",
            status="draft",
            updated_by=admin_email,
        )
    )
    products = db.scalars(
        select(CatalogProduct)
        .where(CatalogProduct.product_code.in_([item[0] for item in DEMO_PRODUCTS]))
        .order_by(CatalogProduct.product_code)
    ).all()
    presentation = sub_events[1]
    for position, product in enumerate(products, start=1):
        _, _, description = DEMO_PRODUCT_DETAILS[product.product_code]
        db.add(
            EventProductSlide(
                event_id=event.id,
                sub_event_id=presentation.id,
                position=position,
                catalog_product_code=product.product_code,
                model_number=product.model_number or product.product_code,
                name=product.name,
                vendor_code=product.vendor_code,
                description=description,
                specifications="Event demonstration offer · New condition · Manufacturer warranty",
                event_unit_cost=product.unit_price,
                standard_cost=product.unit_price,
                currency=product.currency,
                minimum_order_quantity=int(product.minimum_order_quantity),
                available_inventory=100,
                max_event_units=100,
                allow_waitlist=True,
                delivery_window_start=date(2026, 8, 20),
                delivery_window_end=date(2026, 9, 30),
                status="ready",
                created_by=admin_email,
            )
        )
    db.flush()
    _ensure_demo_operations(db, event, admin_email)
    db.commit()
    db.refresh(event)
    return event
