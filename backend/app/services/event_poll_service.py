from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.event_management import (
    EventPoll,
    EventPollOption,
    EventPollVote,
    EventProductSlide,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_poll import (
    EventPollCreate,
    EventPollOptionResponse,
    EventPollResponse,
)
from app.services.event_access_service import (
    active_event_membership,
    event_operations_are_locked,
    membership_has_sub_event_access,
)


class EventPollError(ValueError):
    pass


def _polling_enabled(sub_event: ManagedSubEvent) -> None:
    if "polling" not in sub_event.module_codes:
        raise EventPollError("Polling is not enabled for this sub-event")


def _poll_query():
    return select(EventPoll).options(selectinload(EventPoll.options))


def _response(db: Session, poll: EventPoll, user_id: int | None) -> EventPollResponse:
    counts = dict(
        db.execute(
            select(EventPollVote.option_id, func.count(EventPollVote.id))
            .where(EventPollVote.poll_id == poll.id)
            .group_by(EventPollVote.option_id)
        ).all()
    )
    selected = None
    if user_id is not None:
        selected = db.scalar(
            select(EventPollVote.option_id).where(
                EventPollVote.poll_id == poll.id, EventPollVote.user_id == user_id
            )
        )
    total = sum(counts.values())
    reveal = poll.show_results or poll.status == "closed" or user_id is None
    return EventPollResponse(
        id=poll.id,
        event_id=poll.event_id,
        sub_event_id=poll.sub_event_id,
        slide_id=poll.slide_id,
        question=poll.question,
        status=poll.status,
        show_results=poll.show_results,
        total_votes=total if reveal else 0,
        selected_option_id=selected,
        options=[
            EventPollOptionResponse(
                id=option.id,
                position=option.position,
                label=option.label,
                vote_count=counts.get(option.id, 0) if reveal else 0,
                percentage=(counts.get(option.id, 0) / total * 100) if reveal and total else 0,
            )
            for option in poll.options
        ],
        created_at=poll.created_at,
        opened_at=poll.opened_at,
        closed_at=poll.closed_at,
    )


def list_polls(db: Session, sub_event_id: str) -> list[EventPollResponse] | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _polling_enabled(sub_event)
    polls = db.scalars(
        _poll_query().where(EventPoll.sub_event_id == sub_event_id).order_by(EventPoll.created_at)
    ).all()
    return [_response(db, poll, None) for poll in polls]


def create_poll(
    db: Session, sub_event_id: str, payload: EventPollCreate, actor: str
) -> EventPollResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _polling_enabled(sub_event)
    if event_operations_are_locked(db, sub_event.event_id):
        raise EventPollError(
            "Event polls are locked because the event is cancelled or settlement is closed"
        )
    if payload.slide_id:
        slide = db.get(EventProductSlide, payload.slide_id)
        if slide is None or slide.sub_event_id != sub_event_id:
            raise EventPollError("Product slide does not belong to this sub-event")
    poll = EventPoll(
        event_id=sub_event.event_id,
        sub_event_id=sub_event_id,
        slide_id=payload.slide_id,
        question=payload.question.strip(),
        status="draft",
        show_results=payload.show_results,
        created_by=actor,
    )
    poll.options = [
        EventPollOption(position=position, label=label.strip())
        for position, label in enumerate(payload.options, start=1)
    ]
    db.add(poll)
    db.commit()
    poll = db.scalar(_poll_query().where(EventPoll.id == poll.id))
    return _response(db, poll, None)


def set_poll_status(db: Session, poll_id: str, status: str) -> EventPollResponse | None:
    poll = db.scalar(_poll_query().where(EventPoll.id == poll_id).with_for_update())
    if poll is None:
        return None
    if event_operations_are_locked(db, poll.event_id):
        raise EventPollError("Event polls are locked because the event is archived")
    _polling_enabled(db.get(ManagedSubEvent, poll.sub_event_id))
    now = datetime.now(UTC)
    if status == "open":
        for other in db.scalars(
            select(EventPoll).where(
                EventPoll.sub_event_id == poll.sub_event_id,
                EventPoll.status == "open",
                EventPoll.id != poll.id,
            )
        ).all():
            other.status = "closed"
            other.closed_at = now
        poll.status = "open"
        poll.opened_at = now
        poll.closed_at = None
    else:
        poll.status = "closed"
        poll.closed_at = now
    db.commit()
    poll = db.scalar(_poll_query().where(EventPoll.id == poll_id))
    return _response(db, poll, None)


def _member(db: Session, poll: EventPoll, user: User) -> bool:
    membership = active_event_membership(db, poll.event_id, user.id)
    return bool(membership and membership_has_sub_event_access(db, membership, poll.sub_event_id))


def active_poll(db: Session, sub_event_id: str, user: User) -> EventPollResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _polling_enabled(sub_event)
    poll = db.scalar(
        _poll_query().where(EventPoll.sub_event_id == sub_event_id, EventPoll.status == "open")
    )
    if poll is None:
        return None
    _polling_enabled(db.get(ManagedSubEvent, poll.sub_event_id))
    if not _member(db, poll, user):
        raise EventPollError("Event membership is required")
    return _response(db, poll, user.id)


def cast_vote(db: Session, poll_id: str, option_id: str, user: User) -> EventPollResponse | None:
    poll = db.scalar(_poll_query().where(EventPoll.id == poll_id).with_for_update())
    if poll is None:
        return None
    if event_operations_are_locked(db, poll.event_id):
        raise EventPollError(
            "Event polls are locked because the event is cancelled or settlement is closed"
        )
    if not _member(db, poll, user):
        raise EventPollError("Event membership is required")
    if poll.status != "open":
        raise EventPollError("Poll is not open")
    if option_id not in {option.id for option in poll.options}:
        raise EventPollError("Poll option was not found")
    existing = db.scalar(
        select(EventPollVote.id).where(
            EventPollVote.poll_id == poll.id, EventPollVote.user_id == user.id
        )
    )
    if existing is not None:
        raise EventPollError("You have already voted in this poll")
    db.add(EventPollVote(poll_id=poll.id, option_id=option_id, user_id=user.id))
    db.commit()
    poll = db.scalar(_poll_query().where(EventPoll.id == poll_id))
    return _response(db, poll, user.id)
