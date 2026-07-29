from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.event_management import (
    EventEntityOrder,
    EventEntityOrderRevision,
    EventMembership,
    EventPresentationState,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_ordering import (
    EventEntityOrderResponse,
    EventEntityOrderWrite,
    EventOrderingAssignmentResponse,
    EventOrderingWorkspaceResponse,
)
from app.schemas.event_product_slide import EventProductSlideResponse
from app.services.event_access_service import (
    event_operations_are_locked,
    membership_has_sub_event_access,
)


class EventOrderingError(ValueError):
    pass


def _ordering_enabled(sub_event: ManagedSubEvent) -> None:
    if "ordering" not in sub_event.module_codes:
        raise EventOrderingError("Ordering is not enabled for this sub-event")


def _order_capacity(slide: EventProductSlide | None) -> int | None:
    if slide is None:
        return None
    limits = [
        value for value in (slide.max_event_units, slide.available_inventory) if value is not None
    ]
    return min(limits) if limits else None


def list_ordering_assignments(db: Session, user: User) -> list[EventOrderingAssignmentResponse]:
    rows = db.execute(
        select(ManagedEvent, ManagedSubEvent, EventMembership)
        .join(ManagedSubEvent, ManagedSubEvent.event_id == ManagedEvent.id)
        .join(EventMembership, EventMembership.event_id == ManagedEvent.id)
        .where(
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "franchise_representative",
            EventMembership.entity_code.is_not(None),
            EventMembership.is_active.is_(True),
            ManagedSubEvent.status != "cancelled",
        )
        .order_by(ManagedSubEvent.starts_at)
    ).all()
    return [
        EventOrderingAssignmentResponse(
            event_id=event.id,
            event_name=event.name,
            sub_event_id=sub_event.id,
            sub_event_name=sub_event.name,
            starts_at=sub_event.starts_at,
            ends_at=sub_event.ends_at,
            location=sub_event.location,
            entity_code=membership.entity_code,
        )
        for event, sub_event, membership in rows
        if "ordering" in sub_event.module_codes
        and membership_has_sub_event_access(db, membership, sub_event.id)
    ]


def _membership(
    db: Session, event_id: str, sub_event_id: str, user: User
) -> EventMembership | None:
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "franchise_representative",
            EventMembership.entity_code.is_not(None),
            EventMembership.is_active.is_(True),
        )
    )
    if membership and membership_has_sub_event_access(db, membership, sub_event_id):
        return membership
    return None


def ordering_workspace(
    db: Session, sub_event_id: str, user: User
) -> EventOrderingWorkspaceResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _ordering_enabled(sub_event)
    membership = _membership(db, sub_event.event_id, sub_event_id, user)
    if membership is None:
        raise EventOrderingError("An active entity ordering assignment is required")
    event = db.get(ManagedEvent, sub_event.event_id)
    state = db.get(EventPresentationState, sub_event_id)
    slide = None
    if state and state.current_slide_id:
        slide = db.scalar(
            select(EventProductSlide)
            .options(selectinload(EventProductSlide.image))
            .where(EventProductSlide.id == state.current_slide_id)
        )
    order = None
    if slide:
        order = db.scalar(
            select(EventEntityOrder).where(
                EventEntityOrder.sub_event_id == sub_event_id,
                EventEntityOrder.slide_id == slide.id,
                EventEntityOrder.entity_code == membership.entity_code,
            )
        )
    confirmed = 0
    if slide:
        confirmed = (
            db.scalar(
                select(func.coalesce(func.sum(EventEntityOrder.quantity), 0)).where(
                    EventEntityOrder.slide_id == slide.id,
                    EventEntityOrder.status == "confirmed",
                )
            )
            or 0
        )
    cap = _order_capacity(slide)
    entity_sub_event_spend = db.scalar(
        select(func.coalesce(func.sum(EventEntityOrder.total_cost), 0)).where(
            EventEntityOrder.sub_event_id == sub_event.id,
            EventEntityOrder.entity_code == membership.entity_code,
            EventEntityOrder.status.in_(["confirmed", "waitlisted"]),
        )
    ) or Decimal("0.00")
    return EventOrderingWorkspaceResponse(
        event_id=sub_event.event_id,
        event_name=event.name,
        sub_event_id=sub_event.id,
        sub_event_name=sub_event.name,
        entity_code=membership.entity_code,
        ordering_status=(
            "open"
            if not event_operations_are_locked(db, sub_event.event_id)
            and state
            and state.ordering_status == "open"
            and slide is not None
            and slide.slide_type == "product"
            else "closed"
        ),
        ordering_opened_at=state.ordering_opened_at if state else None,
        presentation_status=state.status if state else "idle",
        current_slide=(
            EventProductSlideResponse.model_validate(slide, from_attributes=True).model_copy(
                update={
                    "has_image": slide.image is not None,
                    "presenter_notes": None,
                }
            )
            if slide
            else None
        ),
        existing_order=EventEntityOrderResponse.model_validate(order) if order else None,
        units_remaining=max(cap - confirmed, 0) if cap is not None else None,
        entity_sub_event_spend=entity_sub_event_spend,
    )


def submit_entity_order(
    db: Session,
    sub_event_id: str,
    payload: EventEntityOrderWrite,
    user: User,
) -> EventOrderingWorkspaceResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _ordering_enabled(sub_event)
    if event_operations_are_locked(db, sub_event.event_id):
        raise EventOrderingError(
            "Event ordering is locked because the event is cancelled or settlement is closed"
        )
    membership = _membership(db, sub_event.event_id, sub_event_id, user)
    if membership is None:
        raise EventOrderingError("An active entity ordering assignment is required")
    state = db.scalar(
        select(EventPresentationState)
        .where(EventPresentationState.sub_event_id == sub_event_id)
        .with_for_update()
    )
    if state is None or state.status != "live" or state.ordering_status != "open":
        raise EventOrderingError("Ordering is not open for the current product")
    slide = db.get(EventProductSlide, state.current_slide_id)
    if slide is None or slide.slide_type != "product":
        raise EventOrderingError("No current product is available")
    if (
        slide.event_unit_cost is None
        or slide.delivery_window_start is None
        or slide.delivery_window_end is None
    ):
        raise EventOrderingError("Current product ordering details are incomplete")
    variant_quantities = {
        model: quantity for model, quantity in payload.variant_quantities.items() if quantity > 0
    }
    variants = {item["model_number"]: item for item in (slide.product_variants or [])}
    if variants:
        unknown = sorted(set(variant_quantities) - set(variants))
        if unknown:
            raise EventOrderingError(f"Unknown product variants: {', '.join(unknown)}")
        if not variant_quantities:
            raise EventOrderingError("Enter a quantity for at least one product variant")
        for model, quantity in variant_quantities.items():
            minimum = int(variants[model].get("minimum_order_quantity", 1))
            if quantity < minimum:
                raise EventOrderingError(f"{model} requires a minimum quantity of {minimum}")
        requested_quantity = sum(variant_quantities.values())
        requested_total = sum(
            Decimal(str(variants[model]["event_unit_cost"])) * quantity
            for model, quantity in variant_quantities.items()
        )
    else:
        requested_quantity = payload.quantity
        requested_total = Decimal(payload.quantity) * slide.event_unit_cost
    if requested_quantity < slide.minimum_order_quantity:
        raise EventOrderingError(
            f"Quantity must meet the minimum order quantity of {slide.minimum_order_quantity}"
        )
    order = db.scalar(
        select(EventEntityOrder).where(
            EventEntityOrder.sub_event_id == sub_event_id,
            EventEntityOrder.slide_id == slide.id,
            EventEntityOrder.entity_code == membership.entity_code,
        )
    )
    confirmed_other = (
        db.scalar(
            select(func.coalesce(func.sum(EventEntityOrder.quantity), 0)).where(
                EventEntityOrder.slide_id == slide.id,
                EventEntityOrder.status == "confirmed",
                EventEntityOrder.id != (order.id if order else ""),
            )
        )
        or 0
    )
    cap = _order_capacity(slide)
    over_cap = cap is not None and confirmed_other + requested_quantity > cap
    if over_cap and not slide.allow_waitlist:
        raise EventOrderingError("Requested quantity exceeds remaining event availability")
    status = "waitlisted" if over_cap else "confirmed"
    if order is None:
        order = EventEntityOrder(
            event_id=sub_event.event_id,
            sub_event_id=sub_event_id,
            slide_id=slide.id,
            membership_id=membership.id,
            user_id=user.id,
            entity_code=membership.entity_code,
        )
        db.add(order)
    order.quantity = requested_quantity
    order.variant_quantities = variant_quantities
    # Franchise representatives choose quantities only. The vendor-scoped
    # delivery window remains authoritative for downstream review and release.
    order.requested_delivery_start = slide.delivery_window_start
    order.requested_delivery_end = slide.delivery_window_end
    order.unit_cost = slide.event_unit_cost
    order.total_cost = requested_total
    order.status = status
    db.flush()
    revision = (
        db.scalar(
            select(func.count(EventEntityOrderRevision.id)).where(
                EventEntityOrderRevision.order_id == order.id
            )
        )
        or 0
    )
    db.add(
        EventEntityOrderRevision(
            order_id=order.id,
            revision=revision + 1,
            quantity=requested_quantity,
            requested_delivery_start=slide.delivery_window_start,
            requested_delivery_end=slide.delivery_window_end,
            status=status,
            changed_by=user.email,
        )
    )
    db.commit()
    return ordering_workspace(db, sub_event_id, user)
