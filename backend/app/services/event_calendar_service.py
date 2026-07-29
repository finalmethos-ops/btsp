from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.event_management import (
    EventCalendarEntry,
    EventMembership,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.event_snapshot import EventSnapshot
from app.models.identity import User
from app.schemas.event_calendar import (
    EventCalendarEntryResponse,
    EventCalendarEntryWrite,
)
from app.services.event_access_service import (
    event_operations_are_locked,
    membership_has_sub_event_access,
)


class EventCalendarError(ValueError):
    pass


def _query():
    return select(EventCalendarEntry).options(selectinload(EventCalendarEntry.sub_event))


def _response(db: Session, entry: EventCalendarEntry) -> EventCalendarEntryResponse:
    event = db.get(ManagedEvent, entry.event_id)
    sub_event = entry.sub_event
    linked = entry.entry_type == "sub_event" and sub_event is not None
    return EventCalendarEntryResponse(
        id=entry.id,
        event_id=entry.event_id,
        event_name=event.name,
        entry_type=entry.entry_type,
        sub_event_id=entry.sub_event_id,
        module_codes=sub_event.module_codes if linked else [],
        title=sub_event.name if linked else entry.title,
        description=sub_event.description if linked else entry.description,
        starts_at=sub_event.starts_at if linked else entry.starts_at,
        ends_at=sub_event.ends_at if linked else entry.ends_at,
        location=sub_event.location if linked else entry.location,
        visibility_categories=entry.visibility_categories,
        is_active=entry.is_active,
        sub_event_accessible=True,
        updated_at=entry.updated_at,
    )


def _sub_event_response(
    event: ManagedEvent, sub_event: ManagedSubEvent
) -> EventCalendarEntryResponse:
    """Return a calendar entry for a sub-event without requiring manual setup."""
    return EventCalendarEntryResponse(
        id=f"subevent:{sub_event.id}",
        event_id=event.id,
        event_name=event.name,
        entry_type="sub_event",
        sub_event_id=sub_event.id,
        module_codes=sub_event.module_codes or [],
        title=sub_event.name,
        description=sub_event.description,
        starts_at=sub_event.starts_at,
        ends_at=sub_event.ends_at,
        location=sub_event.location,
        visibility_categories=[
            "staff",
            "vendor",
            "franchise_representative",
            "executive",
            "admin",
        ],
        is_active=True,
        sub_event_accessible=True,
        updated_at=sub_event.created_at,
    )


def list_event_calendar(db: Session, event_id: str) -> list[EventCalendarEntryResponse] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    entries = db.scalars(
        _query()
        .where(EventCalendarEntry.event_id == event_id)
        .order_by(EventCalendarEntry.starts_at, EventCalendarEntry.title)
    ).all()
    responses = [_response(db, entry) for entry in entries]
    linked_ids = {entry.sub_event_id for entry in responses if entry.sub_event_id}
    event = db.scalar(
        select(ManagedEvent)
        .options(selectinload(ManagedEvent.sub_events))
        .where(ManagedEvent.id == event_id)
    )
    if event:
        responses.extend(
            _sub_event_response(event, sub_event)
            for sub_event in event.sub_events
            if sub_event.status != "cancelled" and sub_event.id not in linked_ids
        )
    return sorted(responses, key=lambda item: (item.starts_at, item.title))


def save_calendar_entry(
    db: Session,
    event_id: str,
    payload: EventCalendarEntryWrite,
    actor: str,
    entry_id: str | None = None,
) -> EventCalendarEntryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventCalendarError(
            "Event calendar is locked because the event is cancelled or settlement is closed"
        )
    if payload.sub_event_id:
        sub_event = db.get(ManagedSubEvent, payload.sub_event_id)
        if sub_event is None or sub_event.event_id != event_id:
            raise EventCalendarError("Sub-event does not belong to this event")
    entry = db.get(EventCalendarEntry, entry_id) if entry_id else None
    if entry_id and (entry is None or entry.event_id != event_id):
        return None
    if entry is None:
        entry = EventCalendarEntry(event_id=event_id, created_by=actor)
        db.add(entry)
    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    db.commit()
    return _response(db, db.scalar(_query().where(EventCalendarEntry.id == entry.id)))


def remove_calendar_entry(db: Session, event_id: str, entry_id: str, actor: str) -> bool:
    if event_operations_are_locked(db, event_id):
        raise EventCalendarError("Event calendar is locked because the event is archived")
    entry = db.scalar(
        select(EventCalendarEntry).where(
            EventCalendarEntry.id == entry_id,
            EventCalendarEntry.event_id == event_id,
        )
    )
    if entry is None:
        return False
    db.add(
        EventSnapshot(
            event_type="event.calendar_entry.deleted",
            entity_type="event_calendar_entry",
            entity_id=entry.id,
            actor=actor,
            payload={
                "event_id": event_id,
                "title": entry.title,
                "entry_type": entry.entry_type,
                "sub_event_id": entry.sub_event_id,
                "starts_at": entry.starts_at.isoformat(),
            },
        )
    )
    db.delete(entry)
    db.commit()
    return True


def my_calendar(db: Session, user: User, platform_admin: bool) -> list[EventCalendarEntryResponse]:
    entries = db.scalars(
        _query()
        .where(EventCalendarEntry.is_active.is_(True))
        .order_by(EventCalendarEntry.starts_at, EventCalendarEntry.title)
    ).all()
    memberships = {
        item.event_id: item
        for item in db.scalars(
            select(EventMembership).where(
                EventMembership.user_id == user.id,
                EventMembership.is_active.is_(True),
            )
        ).all()
    }
    visible = []
    visible_sub_events: set[tuple[str, str]] = set()
    for entry in entries:
        membership = memberships.get(entry.event_id)
        hide_unregistered_sub_events = bool(
            membership and membership.membership_type in {"vendor", "franchise_representative"}
        )
        if not platform_admin:
            if membership is None or membership.membership_type not in entry.visibility_categories:
                continue
        if entry.sub_event and entry.sub_event.status == "cancelled":
            continue
        response = _response(db, entry)
        response.sub_event_accessible = bool(
            not entry.sub_event_id
            or membership_has_sub_event_access(db, membership, entry.sub_event_id)
        )
        if (
            hide_unregistered_sub_events
            and entry.sub_event_id
            and not response.sub_event_accessible
        ):
            continue
        visible.append(response)
        if entry.sub_event_id:
            visible_sub_events.add((entry.event_id, entry.sub_event_id))

    event_ids = (
        set(memberships)
        if not platform_admin
        else {
            event_id
            for (event_id,) in db.execute(
                select(ManagedEvent.id).where(ManagedEvent.status.in_(("draft", "published")))
            )
        }
    )
    if event_ids:
        events = db.scalars(
            select(ManagedEvent)
            .options(selectinload(ManagedEvent.sub_events))
            .where(ManagedEvent.id.in_(event_ids))
        ).all()
        for event in events:
            membership = memberships.get(event.id)
            hide_unregistered_sub_events = bool(
                membership and membership.membership_type in {"vendor", "franchise_representative"}
            )
            for sub_event in event.sub_events:
                if (
                    sub_event.status == "cancelled"
                    or (event.id, sub_event.id) in visible_sub_events
                ):
                    continue
                response = _sub_event_response(event, sub_event)
                response.sub_event_accessible = bool(
                    platform_admin or membership_has_sub_event_access(db, membership, sub_event.id)
                )
                if hide_unregistered_sub_events and not response.sub_event_accessible:
                    continue
                visible.append(response)
    return sorted(visible, key=lambda item: (item.starts_at, item.title))
