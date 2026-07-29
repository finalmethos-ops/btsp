from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_management import (
    EventMembership,
    ManagedEvent,
    ManagedSubEvent,
    VendorHallInventoryItem,
)
from app.models.identity import Role, User
from app.models.purchasing import PurchaseRequest
from app.models.store import Store
from app.schemas.event_buy_fair import (
    EventBuyFairModel,
    EventBuyFairOrderCreate,
    EventBuyFairOrderSummary,
    EventBuyFairRequester,
    EventBuyFairStore,
    EventBuyFairSummary,
    EventBuyFairVendorSummary,
    EventBuyFairWorkspace,
)
from app.schemas.purchasing import PurchaseRequestResponse
from app.services.event_access_service import (
    event_operations_are_locked,
    membership_has_sub_event_access,
)
from app.services.order_lifecycle_service import create_vendor_requests
from app.services.vendor_geography_service import eligible_stores


class EventBuyFairError(ValueError):
    pass


def _vendor_name_key(value: str | None) -> str:
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _access(
    db: Session, sub_event_id: str, user: User, *, lock_event: bool = False
) -> tuple[ManagedEvent, ManagedSubEvent, EventMembership]:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        raise EventBuyFairError("Vendor buy fair was not found")
    if "vendor-buy-fair" not in sub_event.module_codes:
        raise EventBuyFairError("Vendor buy fair ordering is not enabled for this sub-event")
    event_statement = select(ManagedEvent).where(ManagedEvent.id == sub_event.event_id)
    if lock_event:
        event_statement = event_statement.with_for_update()
    event = db.scalar(event_statement)
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == sub_event.event_id,
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "vendor",
            EventMembership.is_active.is_(True),
        )
    )
    selected_vendor = user.vendor_code or membership.vendor_code if membership else None
    allowed_vendors = set(membership.vendor_codes or []) if membership else set()
    if membership and membership.vendor_code:
        allowed_vendors.add(membership.vendor_code)
    if event is None or membership is None or not selected_vendor:
        raise EventBuyFairError("An active vendor event assignment is required")
    vendor_allowed = selected_vendor in allowed_vendors
    if not vendor_allowed:
        selected = db.scalar(
            select(CatalogVendor).where(CatalogVendor.vendor_code == selected_vendor)
        )
        selected_name = _vendor_name_key(selected.name if selected else None)
        registered_vendors = db.scalars(
            select(CatalogVendor).where(CatalogVendor.vendor_code.in_(allowed_vendors))
        ).all()
        vendor_allowed = bool(selected_name) and any(
            (alias_name := _vendor_name_key(vendor.name))
            and (
                selected_name == alias_name
                or selected_name in alias_name
                or alias_name in selected_name
            )
            for vendor in registered_vendors
        )
    if not vendor_allowed:
        raise EventBuyFairError("This vendor account is not approved for the event")
    set_committed_value(membership, "vendor_code", selected_vendor)
    if not membership_has_sub_event_access(db, membership, sub_event_id):
        raise EventBuyFairError("This vendor is not assigned to the selected sub-event")
    return event, sub_event, membership


def _event_orders(
    db: Session,
    event_id: str,
    vendor_code: str,
    *,
    sub_event_id: str | None = None,
    include_cancelled: bool = False,
) -> list[PurchaseRequest]:
    candidates = db.scalars(
        select(PurchaseRequest)
        .where(
            PurchaseRequest.workflow_code == "VENDOR_ORDER",
            PurchaseRequest.vendor_code == vendor_code,
        )
        .order_by(PurchaseRequest.created_at.desc())
    ).all()
    return [
        item
        for item in candidates
        if item.context.get("event_id") == event_id
        and (sub_event_id is None or item.context.get("sub_event_id") == sub_event_id)
        and (include_cancelled or item.status != "cancelled_by_vendor")
    ]


def _vendor_workspace_order(item: PurchaseRequest) -> PurchaseRequestResponse:
    response = PurchaseRequestResponse.model_validate(item)
    response.context = {
        key: value for key, value in item.context.items() if key != "requester_email"
    }
    return response


def event_buy_fair_summary(
    db: Session, event_id: str, sub_event_id: str | None = None
) -> EventBuyFairSummary | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    if sub_event_id is not None:
        sub_event = db.get(ManagedSubEvent, sub_event_id)
        if sub_event is None or sub_event.event_id != event_id:
            return None
    candidates = (
        db.scalars(
            select(PurchaseRequest)
            .options(selectinload(PurchaseRequest.line_items))
            .where(PurchaseRequest.workflow_code == "VENDOR_ORDER")
            .order_by(PurchaseRequest.created_at.desc())
        )
        .unique()
        .all()
    )
    orders = [
        item
        for item in candidates
        if item.context.get("event_id") == event_id
        and (sub_event_id is None or item.context.get("sub_event_id") == sub_event_id)
        and item.status != "cancelled_by_vendor"
    ]
    orders.sort(key=lambda item: int(item.context.get("event_order_sequence", 0)), reverse=True)
    order_rows = [
        EventBuyFairOrderSummary(
            id=item.id,
            order_number=item.order_number,
            vendor_code=item.vendor_code,
            store_number=item.store_number,
            requester_name=item.context.get("requester_name"),
            requester_email=item.context.get("requester_email"),
            requester_entity_code=item.context.get("requester_entity_code"),
            requester_region_code=item.context.get("requester_region_code"),
            status=item.status,
            expected_delivery_date=item.expected_delivery_date,
            total_units=sum((line.quantity for line in item.line_items), Decimal("0")),
            total_volume=item.total,
            created_at=item.created_at,
        )
        for item in orders
    ]
    vendor_rows = []
    for vendor_code in sorted({item.vendor_code for item in orders}):
        vendor_orders = [item for item in orders if item.vendor_code == vendor_code]
        vendor_rows.append(
            EventBuyFairVendorSummary(
                vendor_code=vendor_code,
                order_count=len(vendor_orders),
                draft_count=sum(item.status == "vendor_draft" for item in vendor_orders),
                submitted_count=sum(
                    item.status == "submitted_to_purchasing" for item in vendor_orders
                ),
                total_units=sum(
                    (line.quantity for order in vendor_orders for line in order.line_items),
                    Decimal("0"),
                ),
                total_volume=sum((item.total for item in vendor_orders), Decimal("0")),
            )
        )
    return EventBuyFairSummary(
        event_id=event_id,
        sub_event_id=sub_event_id,
        vendor_count=len({item.vendor_code for item in orders}),
        order_count=len(orders),
        draft_count=sum(item.status == "vendor_draft" for item in orders),
        submitted_count=sum(item.status == "submitted_to_purchasing" for item in orders),
        total_units=sum(
            (line.quantity for order in orders for line in order.line_items), Decimal("0")
        ),
        total_volume=sum((item.total for item in orders), Decimal("0")),
        vendors=vendor_rows,
        orders=order_rows,
    )


def sub_event_buy_fair_summary(db: Session, sub_event_id: str) -> EventBuyFairSummary | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    return event_buy_fair_summary(db, sub_event.event_id, sub_event_id)


def event_buy_fair_export_rows(
    db: Session, event_id: str
) -> tuple[ManagedEvent, list[list[str]]] | None:
    event = db.get(ManagedEvent, event_id)
    summary = event_buy_fair_summary(db, event_id)
    if event is None or summary is None:
        return None
    rows = [
        [
            "event_name",
            "order_number",
            "vendor_code",
            "store_number",
            "requester_name",
            "requester_email",
            "requester_entity_code",
            "requester_region_code",
            "status",
            "expected_delivery_date",
            "total_units",
            "total_volume",
            "created_at",
        ]
    ]
    rows.extend(
        [
            event.name,
            item.order_number,
            item.vendor_code,
            item.store_number,
            item.requester_name or "",
            item.requester_email or "",
            item.requester_entity_code or "",
            item.requester_region_code or "",
            item.status,
            item.expected_delivery_date.isoformat() if item.expected_delivery_date else "",
            str(item.total_units),
            str(item.total_volume),
            item.created_at.isoformat(),
        ]
        for item in summary.orders
    )
    return event, rows


def sub_event_buy_fair_export_rows(
    db: Session, sub_event_id: str
) -> tuple[ManagedEvent, ManagedSubEvent, list[list[str]]] | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    event = db.get(ManagedEvent, sub_event.event_id)
    summary = event_buy_fair_summary(db, sub_event.event_id, sub_event_id)
    if event is None or summary is None:
        return None
    rows = [
        [
            "event_name",
            "sub_event_name",
            "order_number",
            "vendor_code",
            "store_number",
            "requester_name",
            "requester_email",
            "requester_entity_code",
            "requester_region_code",
            "status",
            "expected_delivery_date",
            "total_units",
            "total_volume",
            "created_at",
        ]
    ]
    rows.extend(
        [
            event.name,
            sub_event.name,
            item.order_number,
            item.vendor_code,
            item.store_number,
            item.requester_name or "",
            item.requester_email or "",
            item.requester_entity_code or "",
            item.requester_region_code or "",
            item.status,
            item.expected_delivery_date.isoformat() if item.expected_delivery_date else "",
            str(item.total_units),
            str(item.total_volume),
            item.created_at.isoformat(),
        ]
        for item in summary.orders
    )
    return event, sub_event, rows


def buy_fair_workspace(db: Session, sub_event_id: str, user: User) -> EventBuyFairWorkspace:
    event, sub_event, membership = _access(db, sub_event_id, user)
    vendor_code = membership.vendor_code or ""
    booth_models = {
        value.casefold()
        for value in db.scalars(
            select(VendorHallInventoryItem.model_number).where(
                VendorHallInventoryItem.event_id == event.id,
                VendorHallInventoryItem.vendor_code == vendor_code,
                VendorHallInventoryItem.model_number.is_not(None),
            )
        )
        if value
    }
    products = list(
        db.scalars(
            select(CatalogProduct).where(
                CatalogProduct.vendor_code == vendor_code,
                CatalogProduct.is_active.is_(True),
                CatalogProduct.is_available.is_(True),
            )
        ).all()
    )
    models = [
        EventBuyFairModel(
            product_code=item.product_code,
            model_identifier=item.model_number or item.product_code,
            name=item.name,
            unit_price=item.unit_price,
            currency=item.currency,
            minimum_order_quantity=item.minimum_order_quantity,
            is_booth_model=bool(item.model_number and item.model_number.casefold() in booth_models),
        )
        for item in products
    ]
    models.sort(key=lambda item: (not item.is_booth_model, item.model_identifier.casefold()))
    orders = _event_orders(db, event.id, vendor_code, sub_event_id=sub_event.id)
    return EventBuyFairWorkspace(
        event_id=event.id,
        event_name=event.name,
        sub_event_id=sub_event.id,
        sub_event_name=sub_event.name,
        vendor_code=vendor_code,
        models=models,
        stores=[
            EventBuyFairStore.model_validate(item, from_attributes=True)
            for item in eligible_stores(db, vendor_code)
        ],
        requesters=[
            EventBuyFairRequester(
                id=item.id,
                display_name=item.display_name,
                entity_code=item.entity_code,
                region_code=item.region_code,
            )
            for item in db.scalars(
                select(User)
                .join(User.roles)
                .where(
                    Role.code == "FRANCHISE_OPERATOR",
                    User.is_active.is_(True),
                )
                .order_by(User.display_name, User.email)
            ).unique()
        ],
        orders=[_vendor_workspace_order(item) for item in orders],
        order_count=len(orders),
        total_units=sum(
            (line.quantity for order in orders for line in order.line_items), Decimal("0")
        ),
        total_volume=sum((order.total for order in orders), Decimal("0")),
    )


def create_buy_fair_orders(
    db: Session, sub_event_id: str, payload: EventBuyFairOrderCreate, user: User
) -> list[PurchaseRequest]:
    event, sub_event, membership = _access(db, sub_event_id, user, lock_event=True)
    if event_operations_are_locked(db, event.id):
        raise EventBuyFairError(
            "Event ordering is locked because the event is cancelled or settlement is closed"
        )
    vendor_code = membership.vendor_code or ""
    requester = db.scalar(
        select(User)
        .join(User.roles)
        .where(
            User.id == payload.requester_id,
            User.is_active.is_(True),
            Role.code == "FRANCHISE_OPERATOR",
        )
    )
    if requester is None:
        raise EventBuyFairError("Select an active Buddy’s requester")
    stores = list(
        db.scalars(select(Store).where(Store.store_number.in_(payload.store_numbers))).all()
    )
    if len(stores) != len(set(payload.store_numbers)):
        raise EventBuyFairError("One or more selected stores no longer exist")
    requester_entity = (requester.entity_code or "").strip().upper()
    requester_region = (requester.region_code or "").strip().upper()
    # “All Stores” means every store in the requester’s assigned entity, not
    # every company/entity in the database. A region-specific approval remains
    # additionally constrained to that region.
    invalid_stores = [
        store.store_number
        for store in stores
        if (requester_entity and (store.entity_code or "").strip().upper() != requester_entity)
        or (
            requester_region
            and requester_region != "ALL_STORES"
            and (store.region_code or "").strip().upper() != requester_region
        )
        or (not requester_entity and not requester_region)
    ]
    if invalid_stores:
        raise EventBuyFairError(
            "Requester is not authorized for stores: " + ", ".join(sorted(invalid_stores))
        )
    existing = _event_orders(db, event.id, vendor_code, include_cancelled=True)
    sequence = max(
        (int(item.context.get("event_order_sequence", 0)) for item in existing),
        default=0,
    )

    def metadata(store_number: str) -> tuple[str, dict[str, object]]:
        nonlocal sequence
        sequence += 1
        return (
            f"{event.name.strip()}-{store_number.strip()}-{vendor_code.strip()}-{sequence:03d}",
            {
                "source": "event_vendor_buy_fair",
                "event_id": event.id,
                "event_name": event.name,
                "sub_event_id": sub_event.id,
                "sub_event_name": sub_event.name,
                "event_order_sequence": sequence,
                "requester_email": requester.email,
                "requester_name": requester.display_name,
                "requester_entity_code": requester.entity_code,
                "requester_region_code": requester.region_code,
            },
        )

    return create_vendor_requests(
        db,
        vendor_code,
        payload.store_numbers,
        user.email,
        payload.expected_delivery_date,
        payload.line_items,
        order_metadata_factory=metadata,
    )


def require_buy_fair_order(
    db: Session, sub_event_id: str, request_id: str, user: User
) -> PurchaseRequest:
    event, _sub_event, membership = _access(db, sub_event_id, user)
    if event_operations_are_locked(db, event.id):
        raise EventBuyFairError(
            "Event ordering is locked because the event is cancelled or settlement is closed"
        )
    request = db.get(PurchaseRequest, request_id)
    if (
        request is None
        or request.vendor_code != membership.vendor_code
        or request.context.get("event_id") != event.id
        or request.context.get("sub_event_id") != sub_event_id
    ):
        raise EventBuyFairError("Event order was not found")
    return request


def cancel_buy_fair_order(db: Session, request: PurchaseRequest, actor: str) -> None:
    if request.status != "vendor_draft":
        raise EventBuyFairError("Only unsubmitted event order drafts can be canceled")
    request.status = "cancelled_by_vendor"
    request.updated_by = actor
    request.context = {**request.context, "cancelled_by": actor}
    db.commit()
