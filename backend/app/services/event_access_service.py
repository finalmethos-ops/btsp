from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_management import (
    EventMembership,
    EventSettlementEvent,
    EventSubEventRegistration,
    ManagedEvent,
)

EVENT_WINDOW_EXEMPT_MEMBERSHIP_TYPES = {
    "admin",
    "executive",
    "staff",
    "team_lead",
    "dockmaster",
    "overseer",
}


def event_window_open_for_user(
    db: Session, event_id: str, user_id: int, now: datetime | None = None
) -> bool:
    membership = active_event_membership(db, event_id, user_id)
    if membership is None:
        return False
    event = db.get(ManagedEvent, event_id)
    if event is None or event.status in {"completed", "cancelled"}:
        return False
    if (
        membership.membership_type in EVENT_WINDOW_EXEMPT_MEMBERSHIP_TYPES
        or membership.loadout_role in {"team_lead", "dockmaster", "overseer"}
    ):
        return True
    if event.status != "published":
        return False
    current = now or datetime.now(UTC)
    starts_at = event.starts_at if event.starts_at.tzinfo else event.starts_at.replace(tzinfo=UTC)
    ends_at = event.ends_at if event.ends_at.tzinfo else event.ends_at.replace(tzinfo=UTC)
    return starts_at <= current <= ends_at


def event_settlement_is_closed(db: Session, event_id: str) -> bool:
    return (
        db.scalar(
            select(EventSettlementEvent.id).where(
                EventSettlementEvent.event_id == event_id,
                EventSettlementEvent.status == "closed",
            )
        )
        is not None
    )


def event_operations_are_locked(db: Session, event_id: str) -> bool:
    event_status = db.scalar(select(ManagedEvent.status).where(ManagedEvent.id == event_id))
    return event_status in {"completed", "cancelled"} or event_settlement_is_closed(db, event_id)


def active_event_membership(db: Session, event_id: str, user_id: int) -> EventMembership | None:
    return db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user_id,
            EventMembership.is_active.is_(True),
        )
    )


def membership_has_sub_event_access(
    db: Session, membership: EventMembership, sub_event_id: str
) -> bool:
    if not membership.sub_event_scope_configured:
        return True
    return (
        db.scalar(
            select(EventSubEventRegistration.id).where(
                EventSubEventRegistration.membership_id == membership.id,
                EventSubEventRegistration.sub_event_id == sub_event_id,
            )
        )
        is not None
    )


def user_has_sub_event_access(db: Session, event_id: str, sub_event_id: str, user_id: int) -> bool:
    membership = active_event_membership(db, event_id, user_id)
    return bool(
        membership
        and event_window_open_for_user(db, event_id, user_id)
        and membership_has_sub_event_access(db, membership, sub_event_id)
    )
