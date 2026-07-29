from datetime import UTC, datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.event_management import (
    EventAnnouncement,
    EventMembership,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_announcement import (
    EventAnnouncementResponse,
    EventAnnouncementWrite,
)
from app.services.event_access_service import (
    event_operations_are_locked,
    membership_has_sub_event_access,
)


class EventAnnouncementError(ValueError):
    pass


def _response(db: Session, item: EventAnnouncement) -> EventAnnouncementResponse:
    event = db.get(ManagedEvent, item.event_id)
    sub_event = db.get(ManagedSubEvent, item.sub_event_id) if item.sub_event_id else None
    return EventAnnouncementResponse(
        id=item.id,
        event_id=item.event_id,
        event_name=event.name,
        sub_event_id=item.sub_event_id,
        sub_event_name=sub_event.name if sub_event else None,
        title=item.title,
        body=item.body,
        severity=item.severity,
        visibility_categories=item.visibility_categories,
        publishes_at=item.publishes_at,
        expires_at=item.expires_at,
        is_active=item.is_active,
        updated_at=item.updated_at,
    )


def list_announcements(db: Session, event_id: str) -> list[EventAnnouncementResponse] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    items = db.scalars(
        select(EventAnnouncement)
        .where(EventAnnouncement.event_id == event_id)
        .order_by(EventAnnouncement.publishes_at.desc())
    ).all()
    return [_response(db, item) for item in items]


def save_announcement(
    db: Session,
    event_id: str,
    payload: EventAnnouncementWrite,
    actor: str,
    announcement_id: str | None = None,
) -> EventAnnouncementResponse | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventAnnouncementError(
            "Event announcements are locked because the event is cancelled or settlement is closed"
        )
    if payload.sub_event_id:
        sub_event = db.get(ManagedSubEvent, payload.sub_event_id)
        if sub_event is None or sub_event.event_id != event_id:
            raise EventAnnouncementError("Sub-event does not belong to this event")
    item = db.get(EventAnnouncement, announcement_id) if announcement_id else None
    if announcement_id and (item is None or item.event_id != event_id):
        return None
    if item is None:
        item = EventAnnouncement(event_id=event_id, created_by=actor)
        db.add(item)
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _response(db, item)


def remove_announcement(db: Session, event_id: str, announcement_id: str) -> bool:
    if event_operations_are_locked(db, event_id):
        raise EventAnnouncementError(
            "Event announcements are locked because the event is cancelled or settlement is closed"
        )
    removed = db.execute(
        delete(EventAnnouncement).where(
            EventAnnouncement.id == announcement_id,
            EventAnnouncement.event_id == event_id,
        )
    ).rowcount
    db.commit()
    return bool(removed)


def my_announcements(db: Session, user: User) -> list[EventAnnouncementResponse]:
    now = datetime.now(UTC)
    items = db.scalars(
        select(EventAnnouncement)
        .where(
            EventAnnouncement.is_active.is_(True),
            EventAnnouncement.publishes_at <= now,
            or_(EventAnnouncement.expires_at.is_(None), EventAnnouncement.expires_at > now),
        )
        .order_by(EventAnnouncement.severity.desc(), EventAnnouncement.publishes_at.desc())
    ).all()
    memberships = {
        membership.event_id: membership
        for membership in db.scalars(
            select(EventMembership).where(
                EventMembership.user_id == user.id,
                EventMembership.is_active.is_(True),
            )
        ).all()
    }
    visible = []
    for item in items:
        membership = memberships.get(item.event_id)
        if membership is None or membership.membership_type not in item.visibility_categories:
            continue
        if item.sub_event_id and not membership_has_sub_event_access(
            db, membership, item.sub_event_id
        ):
            continue
        visible.append(_response(db, item))
    return visible
