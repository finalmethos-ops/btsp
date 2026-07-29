from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_login_context
from app.auth.permissions import require_permission, user_has_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_calendar import EventCalendarEntryResponse, EventCalendarEntryWrite
from app.services.event_access_service import event_window_open_for_user
from app.services.event_calendar_service import (
    EventCalendarError,
    list_event_calendar,
    my_calendar,
    remove_calendar_entry,
    save_calendar_entry,
)

router = APIRouter(prefix="/event-calendar", tags=["event calendar"])


@router.get("/mine", response_model=list[EventCalendarEntryResponse])
def read_my_calendar(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
) -> list[EventCalendarEntryResponse]:
    platform_admin = user_has_permission(user, "events.manage") and login_context != "event"
    entries = my_calendar(db, user, platform_admin)
    if platform_admin:
        return entries
    return [entry for entry in entries if event_window_open_for_user(db, entry.event_id, user.id)]


@router.get("/{event_id}", response_model=list[EventCalendarEntryResponse])
def read_event_calendar(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventCalendarEntryResponse]:
    entries = list_event_calendar(db, event_id)
    if entries is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return entries


@router.post("/{event_id}", response_model=EventCalendarEntryResponse)
def post_calendar_entry(
    event_id: str,
    payload: EventCalendarEntryWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventCalendarEntryResponse:
    try:
        entry = save_calendar_entry(db, event_id, payload, user.email)
    except EventCalendarError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return entry


@router.put("/{event_id}/{entry_id}", response_model=EventCalendarEntryResponse)
def put_calendar_entry(
    event_id: str,
    entry_id: str,
    payload: EventCalendarEntryWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventCalendarEntryResponse:
    try:
        entry = save_calendar_entry(db, event_id, payload, user.email, entry_id)
    except EventCalendarError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Calendar entry not found")
    return entry


@router.delete("/{event_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_entry(
    event_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> Response:
    try:
        removed = remove_calendar_entry(db, event_id, entry_id, user.email)
    except EventCalendarError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Calendar entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
