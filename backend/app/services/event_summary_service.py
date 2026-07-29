from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import user_has_permission
from app.models.catalog import CatalogProduct
from app.models.event_management import (
    EventEntityOrder,
    EventMembership,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.models.purchasing import PurchaseRequest
from app.schemas.event_summary import EventSummaryBreakdown, EventSummaryResponse, EventSummaryRow
from app.services.event_access_service import event_window_open_for_user


class EventSummaryError(ValueError):
    pass


@dataclass(frozen=True)
class _SummaryLine:
    sub_event_id: str
    vendor_code: str
    entity_code: str
    units: int
    spend: Decimal
    department: str


def event_summary(db: Session, event_id: str, user: User) -> EventSummaryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user.id,
            EventMembership.is_active.is_(True),
        )
    )
    is_operations = user_has_permission(user, "events.manage") or (
        membership is not None and membership.membership_type in {"admin", "executive", "staff"}
    )
    if not is_operations and (
        membership is None or not event_window_open_for_user(db, event_id, user.id)
    ):
        raise EventSummaryError("Event summary is only available to registered attendees")
    scope = (
        "operations"
        if is_operations
        else "vendor"
        if membership.membership_type == "vendor"
        else "buddys"
    )
    # In an event session a multi-vendor attendee's active account is scoped on
    # the token and reflected on ``user.vendor_code``. Fall back to the
    # membership default only for the initial (unselected) session.
    vendor_code = (user.vendor_code or membership.vendor_code) if scope == "vendor" else None
    entity_code = user.entity_code or (membership.entity_code if scope == "buddys" else None)
    region_code = user.region_code if scope == "buddys" else None
    statement = (
        select(EventEntityOrder, EventProductSlide.vendor_code, CatalogProduct.department)
        .join(EventProductSlide, EventProductSlide.id == EventEntityOrder.slide_id)
        .outerjoin(
            CatalogProduct,
            CatalogProduct.product_code == EventProductSlide.catalog_product_code,
        )
        .where(EventEntityOrder.event_id == event_id, EventEntityOrder.status == "confirmed")
    )
    if vendor_code:
        statement = statement.where(EventProductSlide.vendor_code == vendor_code)
    if entity_code:
        statement = statement.where(EventEntityOrder.entity_code == entity_code)
    rows = db.execute(statement).all()
    if region_code and region_code != "ALL_STORES":
        # Event orders are entity-scoped; region is retained as metadata for the
        # account and is used by order creation/eligibility checks.
        pass
    summary_lines = [
        _SummaryLine(
            sub_event_id=order.sub_event_id,
            vendor_code=order_vendor,
            entity_code=order.entity_code,
            units=order.quantity,
            spend=order.total_cost,
            department=department or "UNASSIGNED",
        )
        for order, order_vendor, department in rows
    ]
    # Vendor Buy Fair orders flow through the standard PurchaseRequest table.
    # Include them in the same event totals while applying the same scope.
    purchase_requests = db.scalars(
        select(PurchaseRequest).where(
            PurchaseRequest.workflow_code == "VENDOR_ORDER",
            PurchaseRequest.status != "cancelled_by_vendor",
        )
    ).all()
    for request in purchase_requests:
        context = request.context or {}
        if context.get("event_id") != event_id:
            continue
        if vendor_code and request.vendor_code != vendor_code:
            continue
        requester_entity = context.get("requester_entity_code")
        if entity_code and requester_entity != entity_code:
            continue
        by_request_department: dict[str, tuple[int, Decimal]] = {}
        for line in request.line_items:
            department = (
                line.catalog_product.department
                if line.catalog_product and line.catalog_product.department
                else "UNASSIGNED"
            )
            units, spend = by_request_department.get(department, (0, Decimal("0")))
            by_request_department[department] = (
                units + int(line.quantity),
                spend + line.extended_amount,
            )
        for department, (line_units, line_spend) in by_request_department.items():
            summary_lines.append(
                _SummaryLine(
                    sub_event_id=str(context.get("sub_event_id", "")),
                    vendor_code=request.vendor_code,
                    entity_code=str(requester_entity or "UNASSIGNED"),
                    units=line_units,
                    spend=line_spend,
                    department=department,
                )
            )
    by_sub: dict[str, list[_SummaryLine]] = {}
    by_vendor: dict[str, list[_SummaryLine]] = {}
    by_entity: dict[str, list[_SummaryLine]] = {}
    by_department: dict[str, list[_SummaryLine]] = {}
    for line in summary_lines:
        by_sub.setdefault(line.sub_event_id, []).append(line)
        by_vendor.setdefault(line.vendor_code, []).append(line)
        by_entity.setdefault(line.entity_code, []).append(line)
        by_department.setdefault(line.department, []).append(line)
    sub_events = {
        item.id: item
        for item in db.scalars(
            select(ManagedSubEvent).where(ManagedSubEvent.event_id == event_id)
        ).all()
    }

    def totals(items: list[_SummaryLine]) -> tuple[int, int, str]:
        return (
            len(items),
            sum(item.units for item in items),
            f"{sum((item.spend for item in items), Decimal('0')):.2f}",
        )

    def breakdown(source: dict[str, list[_SummaryLine]]) -> list[EventSummaryBreakdown]:
        return [
            EventSummaryBreakdown(
                code=code,
                order_count=totals(items)[0],
                units=totals(items)[1],
                spend=totals(items)[2],
                average_order_spend=(
                    f"{(sum((item.spend for item in items), Decimal('0')) / len(items)):.2f}"
                ),
            )
            for code, items in sorted(source.items())
        ]

    # `rows` contains SQLAlchemy result tuples, while `summary_lines` contains
    # the normalized objects consumed by all breakdown calculations.
    order_count, units, spend = totals(summary_lines)
    return EventSummaryResponse(
        event_id=event.id,
        event_name=event.name,
        scope=scope,
        vendor_code=vendor_code,
        entity_code=entity_code,
        region_code=region_code,
        total_order_count=order_count,
        total_units=units,
        total_spend=spend,
        sub_events=[
            EventSummaryRow(
                sub_event_id=sub_id,
                sub_event_name=sub_events[sub_id].name,
                order_count=totals(items)[0],
                units=totals(items)[1],
                spend=totals(items)[2],
            )
            for sub_id, items in sorted(
                by_sub.items(), key=lambda pair: sub_events[pair[0]].starts_at
            )
        ],
        vendors=breakdown(by_vendor) if is_operations else [],
        entities=breakdown(by_entity) if is_operations else [],
        departments=breakdown(by_department) if is_operations else [],
    )
