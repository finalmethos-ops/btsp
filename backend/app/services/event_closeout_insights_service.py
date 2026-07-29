from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.permissions import user_has_permission
from app.models.event_management import EventFeedbackResponse, EventMembership, ManagedEvent
from app.models.identity import User
from app.schemas.event_closeout_insights import EventCloseoutInsightsResponse
from app.services.event_settlement_service import event_settlement_summary


class EventCloseoutInsightsError(ValueError):
    pass


def event_closeout_insights(
    db: Session, event_id: str, user: User
) -> EventCloseoutInsightsResponse | None:
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
    if not user_has_permission(user, "events.manage") and (
        membership is None or membership.membership_type not in {"executive", "admin"}
    ):
        raise EventCloseoutInsightsError(
            "Executive closeout insights are not assigned to this account"
        )
    summary = event_settlement_summary(db, event_id)
    if summary is None:
        return None
    response_count = (
        db.scalar(
            select(func.count())
            .select_from(EventFeedbackResponse)
            .where(EventFeedbackResponse.event_id == event_id)
        )
        or 0
    )
    eligible_count = (
        db.scalar(
            select(func.count())
            .select_from(EventMembership)
            .where(EventMembership.event_id == event_id, EventMembership.is_active.is_(True))
        )
        or 0
    )
    average_rating = db.scalar(
        select(func.avg(EventFeedbackResponse.rating)).where(
            EventFeedbackResponse.event_id == event_id
        )
    )
    return EventCloseoutInsightsResponse(
        event_id=event.id,
        event_name=event.name,
        status=summary.status,
        vendor_hall_status=summary.vendor_hall_status,
        vendor_hall_closeout_ready=summary.vendor_hall_closeout_ready,
        readiness_percentage=summary.readiness_percentage,
        order_total=summary.order_total,
        order_released=summary.order_released,
        approved_units=summary.approved_units,
        approved_spend=summary.approved_spend,
        loadout_assignment_total=summary.loadout_assignment_total,
        loadout_released=summary.loadout_released,
        open_exception_count=summary.open_exception_count,
        feedback_response_count=response_count,
        feedback_eligible_attendee_count=eligible_count,
        feedback_response_rate=(Decimal(response_count * 100) / Decimal(eligible_count)).quantize(
            Decimal("0.01")
        )
        if eligible_count
        else Decimal("0.00"),
        feedback_average_rating=Decimal(str(average_rating)).quantize(Decimal("0.01"))
        if average_rating is not None
        else None,
        order_to_loadout_rate=(
            Decimal(summary.loadout_released * 100) / Decimal(summary.order_released)
        ).quantize(Decimal("0.01"))
        if summary.order_released
        else Decimal("0.00"),
        approved_at=summary.approved_at,
        closed_at=summary.closed_at,
    )
