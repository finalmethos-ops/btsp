from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_management import (
    EventBrandingAsset,
    EventEntityOrder,
    EventMembership,
    EventPresentationState,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
)
from app.schemas.event_presentation import (
    EventLiveAnalyticsResponse,
    EventLiveEntityOrder,
    EventPresentationQueueItem,
    EventPresentationResponse,
    PresentationAction,
)
from app.schemas.event_product_slide import EventProductSlideResponse
from app.services.event_access_service import event_operations_are_locked


class EventPresentationError(ValueError):
    pass


def _ordering_is_open(state: EventPresentationState | None) -> bool:
    return bool(state and state.ordering_status == "open")


def _live_display_enabled(sub_event: ManagedSubEvent) -> None:
    if not {"live-display", "product-slides"}.intersection(sub_event.module_codes):
        raise EventPresentationError("Live Display is not enabled for this sub-event")


def _ensure_projectable(slide: EventProductSlide) -> None:
    if slide.filler_category == "full_screen_image" and slide.image is None:
        raise EventPresentationError(
            f'Upload an image for full-screen slide "{slide.name}" before presenting'
        )


def get_live_analytics(db: Session, sub_event_id: str) -> EventLiveAnalyticsResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _live_display_enabled(sub_event)
    state = db.get(EventPresentationState, sub_event_id)
    slide_id = state.current_slide_id if state else None
    assigned = (
        db.scalar(
            select(func.count(func.distinct(EventMembership.entity_code))).where(
                EventMembership.event_id == sub_event.event_id,
                EventMembership.membership_type == "franchise_representative",
                EventMembership.entity_code.is_not(None),
                EventMembership.is_active.is_(True),
            )
        )
        or 0
    )
    orders = []
    if slide_id:
        orders = list(
            db.scalars(
                select(EventEntityOrder)
                .where(EventEntityOrder.slide_id == slide_id)
                .order_by(EventEntityOrder.updated_at.desc())
            ).all()
        )
    confirmed = [order for order in orders if order.status == "confirmed"]
    waitlisted = [order for order in orders if order.status == "waitlisted"]
    return EventLiveAnalyticsResponse(
        sub_event_id=sub_event_id,
        current_slide_id=slide_id,
        assigned_entities=assigned,
        responding_entities=len(orders),
        confirmed_entities=len(confirmed),
        waitlisted_entities=len(waitlisted),
        entities_remaining=max(assigned - len(orders), 0),
        confirmed_units=sum(order.quantity for order in confirmed),
        confirmed_spend=f"{sum(order.total_cost for order in confirmed):.2f}",
        waitlisted_units=sum(order.quantity for order in waitlisted),
        orders=[
            EventLiveEntityOrder(
                entity_code=order.entity_code,
                quantity=order.quantity,
                total_cost=f"{order.total_cost:.2f}",
                status=order.status,
                updated_at=order.updated_at,
            )
            for order in orders
        ],
    )


def _slides(db: Session, sub_event_id: str) -> list[EventProductSlide]:
    return list(
        db.scalars(
            select(EventProductSlide)
            .options(selectinload(EventProductSlide.image))
            .where(
                EventProductSlide.sub_event_id == sub_event_id,
                EventProductSlide.status != "archived",
            )
            .order_by(EventProductSlide.position)
        ).all()
    )


def get_presentation(
    db: Session,
    sub_event_id: str,
    *,
    include_presenter_details: bool = False,
) -> EventPresentationResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _live_display_enabled(sub_event)
    event = db.get(ManagedEvent, sub_event.event_id)
    state = db.get(EventPresentationState, sub_event_id)
    slides = _slides(db, sub_event_id)
    current = next(
        (slide for slide in slides if state and slide.id == state.current_slide_id), None
    )
    current_response = None
    if current is not None:
        product = (
            db.scalar(
                select(CatalogProduct).where(
                    CatalogProduct.product_code == current.catalog_product_code
                )
            )
            if current.catalog_product_code
            else None
        )
        vendor_name = (
            db.scalar(
                select(CatalogVendor.name).where(CatalogVendor.vendor_code == current.vendor_code)
            )
            if current.vendor_code
            else None
        )
        current_response = EventProductSlideResponse.model_validate(
            current, from_attributes=True
        ).model_copy(
            update={
                "has_image": current.image is not None,
                "presenter_notes": None,
                "vendor_name": vendor_name,
                "category": current.category
                or (product.product_category_code or product.department if product else None),
            }
        )
    total_units = 0
    total_spend = "0.00"
    variant_units_ordered: dict[str, int] = {}
    if current is not None:
        current_orders = list(
            db.scalars(
                select(EventEntityOrder).where(
                    EventEntityOrder.slide_id == current.id,
                    EventEntityOrder.status == "confirmed",
                )
            ).all()
        )
        total_units = sum(order.quantity for order in current_orders)
        total_spend = f"{sum(order.total_cost for order in current_orders):.2f}"
        for order in current_orders:
            for model_number, quantity in (order.variant_quantities or {}).items():
                variant_units_ordered[model_number] = variant_units_ordered.get(
                    model_number, 0
                ) + int(quantity)
    sub_event_totals = db.execute(
        select(
            func.coalesce(func.sum(EventEntityOrder.quantity), 0),
            func.coalesce(func.sum(EventEntityOrder.total_cost), 0),
        ).where(
            EventEntityOrder.sub_event_id == sub_event.id,
            EventEntityOrder.status == "confirmed",
        )
    ).one()
    return EventPresentationResponse(
        sub_event_id=sub_event.id,
        event_id=sub_event.event_id,
        event_name=event.name,
        event_theme_primary_color=event.theme_primary_color,
        event_theme_accent_color=event.theme_accent_color,
        event_has_branding=db.get(EventBrandingAsset, event.id) is not None,
        sub_event_name=sub_event.name,
        status=state.status if state else "idle",
        ordering_status=(
            "open"
            if not event_operations_are_locked(db, sub_event.event_id) and _ordering_is_open(state)
            else "closed"
        ),
        ordering_opened_at=state.ordering_opened_at if state else None,
        current_slide=current_response,
        total_slides=len(slides),
        current_position=current.position if current else None,
        total_units_ordered=total_units,
        total_combined_spend=total_spend,
        variant_units_ordered=variant_units_ordered,
        sub_event_units_ordered=int(sub_event_totals[0]),
        sub_event_combined_spend=f"{sub_event_totals[1]:.2f}",
        presenter_notes=(
            current.presenter_notes if current is not None and include_presenter_details else None
        ),
        slide_queue=(
            [
                EventPresentationQueueItem(
                    id=slide.id,
                    position=slide.position,
                    slide_type=slide.slide_type,
                    filler_category=slide.filler_category,
                    model_number=slide.model_number,
                    name=slide.name,
                    presenter_notes=slide.presenter_notes,
                )
                for slide in slides
            ]
            if include_presenter_details
            else []
        ),
        presenter_slides=(
            [
                EventProductSlideResponse.model_validate(slide, from_attributes=True).model_copy(
                    update={"has_image": slide.image is not None}
                )
                for slide in slides
            ]
            if include_presenter_details
            else []
        ),
        updated_at=state.updated_at if state else None,
    )


def control_presentation(
    db: Session, sub_event_id: str, action: PresentationAction, actor: str
) -> EventPresentationResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _live_display_enabled(sub_event)
    if event_operations_are_locked(db, sub_event.event_id):
        raise EventPresentationError("Presentation locked: event cancelled or settlement is closed")
    slides = _slides(db, sub_event_id)
    if not slides:
        raise EventPresentationError("Add at least one slide before presenting")
    state = db.scalar(
        select(EventPresentationState)
        .where(EventPresentationState.sub_event_id == sub_event_id)
        .with_for_update()
    )
    if state is None:
        state = EventPresentationState(
            sub_event_id=sub_event_id,
            event_id=sub_event.event_id,
            status="idle",
            ordering_status="closed",
            updated_by=actor,
        )
        db.add(state)
    current_index = next(
        (index for index, slide in enumerate(slides) if slide.id == state.current_slide_id),
        0,
    )
    if action == "start":
        _ensure_projectable(slides[0])
        state.current_slide_id = slides[0].id
        state.status = "live"
        state.ordering_status = "closed"
        state.ordering_opened_at = None
    elif state.status != "live":
        raise EventPresentationError("Start the presentation before using live controls")
    elif action == "next":
        next_slide = slides[min(current_index + 1, len(slides) - 1)]
        _ensure_projectable(next_slide)
        state.current_slide_id = next_slide.id
        state.ordering_status = "closed"
        state.ordering_opened_at = None
    elif action == "previous":
        previous_slide = slides[max(current_index - 1, 0)]
        _ensure_projectable(previous_slide)
        state.current_slide_id = previous_slide.id
        state.ordering_status = "closed"
        state.ordering_opened_at = None
    elif action == "open":
        if state.status != "live" or state.current_slide_id is None:
            raise EventPresentationError("Start the presentation before opening ordering")
        current_slide = db.get(EventProductSlide, state.current_slide_id)
        if current_slide is None or current_slide.slide_type != "product":
            raise EventPresentationError("Ordering cannot open on a filler slide")
        state.ordering_status = "open"
        state.ordering_opened_at = datetime.now(UTC)
    elif action == "close":
        state.ordering_status = "closed"
    elif action == "end":
        state.status = "ended"
        state.ordering_status = "closed"
    state.updated_by = actor
    db.commit()
    return get_presentation(db, sub_event_id, include_presenter_details=True)
