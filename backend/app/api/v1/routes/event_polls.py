from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.event_management import EventPoll, ManagedSubEvent
from app.models.identity import User
from app.schemas.event_poll import (
    EventPollCreate,
    EventPollResponse,
    EventPollStatusUpdate,
    EventPollVoteCreate,
)
from app.services.event_access_service import event_window_open_for_user
from app.services.event_poll_service import (
    EventPollError,
    active_poll,
    cast_vote,
    create_poll,
    list_polls,
    set_poll_status,
)
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(prefix="/event-polls", tags=["event polls"])


@router.get("/sub-events/{sub_event_id}", response_model=list[EventPollResponse])
def read_polls(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventPollResponse]:
    try:
        polls = list_polls(db, sub_event_id)
    except EventPollError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if polls is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return polls


@router.post("/sub-events/{sub_event_id}", response_model=EventPollResponse)
async def post_poll(
    sub_event_id: str,
    payload: EventPollCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventPollResponse:
    try:
        poll = create_poll(db, sub_event_id, payload, user.email)
    except EventPollError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if poll is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "poll.created")
    return poll


@router.get("/active/{sub_event_id}", response_model=EventPollResponse | None)
def read_active_poll(
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventPollResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is not None and not event_window_open_for_user(db, sub_event.event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")
    try:
        return active_poll(db, sub_event_id, user)
    except EventPollError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.put("/{poll_id}/status", response_model=EventPollResponse)
async def put_poll_status(
    poll_id: str,
    payload: EventPollStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventPollResponse:
    try:
        poll = set_poll_status(db, poll_id, payload.status)
    except EventPollError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if poll is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    await event_realtime_hub.publish(poll.sub_event_id, "poll.changed")
    return poll


@router.post("/{poll_id}/vote", response_model=EventPollResponse)
async def post_poll_vote(
    poll_id: str,
    payload: EventPollVoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventPollResponse:
    poll_record = db.get(EventPoll, poll_id)
    if poll_record is not None and not event_window_open_for_user(
        db, poll_record.event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")
    try:
        poll = cast_vote(db, poll_id, payload.option_id, user)
    except EventPollError as exc:
        status = 403 if str(exc) == "Event membership is required" else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    if poll is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    await event_realtime_hub.publish(poll.sub_event_id, "poll.voted")
    return poll
