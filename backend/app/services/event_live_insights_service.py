from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.auth.permissions import user_has_permission
from app.models.catalog import CatalogVendor
from app.models.event_management import (
    EventEntityOrder,
    EventMembership,
    EventPresentationState,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_live_insights import (
    EventLiveInsightsResponse,
    VendorLiveProductMetric,
    VendorLiveVendorMetric,
)
from app.services.event_access_service import membership_has_sub_event_access


class EventLiveInsightsError(ValueError):
    pass


def live_insights(db: Session, sub_event_id: str, user: User) -> EventLiveInsightsResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    event = db.get(ManagedEvent, sub_event.event_id)
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == sub_event.event_id,
            EventMembership.user_id == user.id,
            EventMembership.is_active.is_(True),
        )
    )
    is_admin = user_has_permission(user, "events.manage")
    if not is_admin and (
        membership is None or not membership_has_sub_event_access(db, membership, sub_event_id)
    ):
        raise EventLiveInsightsError("Live event insights are not assigned to this account")
    membership_type = membership.membership_type if membership else "admin"
    if not is_admin and membership_type not in {
        "executive",
        "vendor",
        "admin",
        "franchise_representative",
    }:
        raise EventLiveInsightsError(
            "Live event insights require executive, vendor, or franchise access"
        )
    scope = (
        "vendor"
        if membership_type == "vendor"
        else "franchise"
        if membership_type == "franchise_representative"
        else "executive"
    )
    vendor_codes: list[str] = []
    if scope == "vendor" and membership:
        vendor_codes = list(
            dict.fromkeys(
                [
                    code
                    for code in [
                        membership.vendor_code,
                        *(membership.vendor_codes or []),
                    ]
                    if code
                ]
            )
        )
    vendor_code = vendor_codes[0] if len(vendor_codes) == 1 else None
    vendor_names = (
        dict(
            db.execute(
                select(CatalogVendor.vendor_code, CatalogVendor.name).where(
                    CatalogVendor.vendor_code.in_(vendor_codes)
                )
            ).all()
        )
        if vendor_codes
        else {}
    )
    vendor_name = vendor_names.get(vendor_code) if vendor_code else None
    entity_code = membership.entity_code if membership and scope == "franchise" else None
    state = db.get(EventPresentationState, sub_event_id)
    slides = list(
        db.scalars(
            select(EventProductSlide)
            .where(EventProductSlide.sub_event_id == sub_event_id)
            .order_by(EventProductSlide.position)
        ).all()
    )
    current = next(
        (slide for slide in slides if state and slide.id == state.current_slide_id),
        None,
    )

    def totals(*conditions):
        return db.execute(
            select(
                func.coalesce(func.sum(EventEntityOrder.quantity), 0),
                func.coalesce(func.sum(EventEntityOrder.total_cost), 0),
            ).where(EventEntityOrder.status == "confirmed", *conditions)
        ).one()

    sub_totals = totals(EventEntityOrder.sub_event_id == sub_event_id)
    responding = (
        db.scalar(
            select(func.count(distinct(EventEntityOrder.entity_code))).where(
                EventEntityOrder.sub_event_id == sub_event_id,
                EventEntityOrder.status == "confirmed",
            )
        )
        or 0
    )
    product_metrics: list[VendorLiveProductMetric] = []
    vendor_metrics: list[VendorLiveVendorMetric] = []
    vendor_units = 0
    vendor_spend = Decimal("0.00")
    slides_until_next = None
    next_vendor_code = None
    next_vendor_name = None
    franchise_units = 0
    franchise_spend = Decimal("0.00")
    if entity_code:
        franchise_totals = db.execute(
            select(
                func.coalesce(func.sum(EventEntityOrder.quantity), 0),
                func.coalesce(func.sum(EventEntityOrder.total_cost), 0),
            ).where(
                EventEntityOrder.sub_event_id == sub_event_id,
                EventEntityOrder.entity_code == entity_code,
                EventEntityOrder.status.in_(["confirmed", "waitlisted"]),
            )
        ).one()
        franchise_units = int(franchise_totals[0])
        franchise_spend = franchise_totals[1]
    if vendor_codes:
        vendor_slides = [slide for slide in slides if slide.vendor_code in vendor_codes]
        vendor_orders = (
            list(
                db.scalars(
                    select(EventEntityOrder).where(
                        EventEntityOrder.slide_id.in_([slide.id for slide in vendor_slides]),
                        EventEntityOrder.status == "confirmed",
                    )
                ).all()
            )
            if vendor_slides
            else []
        )
        orders_by_slide: dict[str, list[EventEntityOrder]] = {}
        for order in vendor_orders:
            orders_by_slide.setdefault(order.slide_id, []).append(order)
        units_by_vendor = dict.fromkeys(vendor_codes, 0)
        spend_by_vendor = dict.fromkeys(vendor_codes, Decimal("0.00"))
        for slide in vendor_slides:
            slide_vendor_code = str(slide.vendor_code)
            slide_vendor_name = vendor_names.get(slide_vendor_code, slide_vendor_code)
            slide_orders = orders_by_slide.get(slide.id, [])
            if slide.product_variants:
                for variant in slide.product_variants:
                    model = str(variant["model_number"])
                    units = sum(
                        (order.variant_quantities or {}).get(model, 0) for order in slide_orders
                    )
                    spend = Decimal(str(variant["event_unit_cost"])) * units
                    vendor_units += units
                    vendor_spend += spend
                    units_by_vendor[slide_vendor_code] += units
                    spend_by_vendor[slide_vendor_code] += spend
                    product_metrics.append(
                        VendorLiveProductMetric(
                            slide_id=f"{slide.id}:{model}",
                            position=slide.position,
                            vendor_code=slide_vendor_code,
                            vendor_name=slide_vendor_name,
                            model_number=model,
                            name=str(variant["name"]),
                            units_ordered=units,
                            committed_spend=f"{spend:.2f}",
                        )
                    )
            else:
                units = sum(order.quantity for order in slide_orders)
                spend = sum((order.total_cost for order in slide_orders), Decimal("0.00"))
                vendor_units += int(units)
                vendor_spend += spend
                units_by_vendor[slide_vendor_code] += int(units)
                spend_by_vendor[slide_vendor_code] += spend
                product_metrics.append(
                    VendorLiveProductMetric(
                        slide_id=slide.id,
                        position=slide.position,
                        vendor_code=slide_vendor_code,
                        vendor_name=slide_vendor_name,
                        model_number=slide.model_number,
                        name=slide.name,
                        units_ordered=int(units),
                        committed_spend=f"{spend:.2f}",
                    )
                )
        current_position = current.position if current else 0
        vendor_metrics = [
            VendorLiveVendorMetric(
                vendor_code=code,
                vendor_name=vendor_names.get(code, code),
                units_ordered=units_by_vendor[code],
                committed_spend=f"{spend_by_vendor[code]:.2f}",
            )
            for code in sorted(
                vendor_codes,
                key=lambda item: (vendor_names.get(item, item).casefold(), item),
            )
        ]
        future = [slide for slide in vendor_slides if slide.position > current_position]
        if future:
            next_slide = min(future, key=lambda slide: slide.position)
            slides_until_next = next_slide.position - current_position
            next_vendor_code = next_slide.vendor_code
            next_vendor_name = vendor_names.get(
                str(next_slide.vendor_code), str(next_slide.vendor_code)
            )
    return EventLiveInsightsResponse(
        event_id=event.id,
        event_name=event.name,
        sub_event_id=sub_event.id,
        sub_event_name=sub_event.name,
        scope=scope,
        presentation_status=state.status if state else "idle",
        ordering_status=("open" if state and state.ordering_status == "open" else "closed"),
        current_position=current.position if current else None,
        total_slides=len(slides),
        sub_event_units=int(sub_totals[0]),
        sub_event_spend=f"{sub_totals[1]:.2f}",
        responding_entities=int(responding),
        entity_code=entity_code,
        franchise_sub_event_units=franchise_units,
        franchise_sub_event_spend=f"{franchise_spend:.2f}",
        vendor_code=vendor_code,
        vendor_name=vendor_name,
        vendor_sub_event_units=vendor_units,
        vendor_sub_event_spend=f"{vendor_spend:.2f}",
        slides_until_next_product=slides_until_next,
        next_vendor_code=next_vendor_code,
        next_vendor_name=next_vendor_name,
        vendor_totals=vendor_metrics,
        vendor_products=product_metrics,
    )
