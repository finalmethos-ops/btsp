from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_announcement import EventAnnouncementResponse, EventAnnouncementWrite
from app.services.event_access_service import event_window_open_for_user
from app.services.event_announcement_service import (
    EventAnnouncementError,
    list_announcements,
    my_announcements,
    remove_announcement,
    save_announcement,
)

router = APIRouter(prefix="/event-announcements", tags=["event announcements"])


@router.get("/mine", response_model=list[EventAnnouncementResponse])
def read_my_announcements(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EventAnnouncementResponse]:
    return [
        announcement
        for announcement in my_announcements(db, user)
        if event_window_open_for_user(db, announcement.event_id, user.id)
    ]


@router.get("/{event_id}", response_model=list[EventAnnouncementResponse])
def read_announcements(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventAnnouncementResponse]:
    items = list_announcements(db, event_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return items


@router.post("/{event_id}", response_model=EventAnnouncementResponse)
def post_announcement(
    event_id: str,
    payload: EventAnnouncementWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventAnnouncementResponse:
    try:
        item = save_announcement(db, event_id, payload, user.email)
    except EventAnnouncementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return item


@router.put("/{event_id}/{announcement_id}", response_model=EventAnnouncementResponse)
def put_announcement(
    event_id: str,
    announcement_id: str,
    payload: EventAnnouncementWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventAnnouncementResponse:
    try:
        item = save_announcement(db, event_id, payload, user.email, announcement_id)
    except EventAnnouncementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return item


@router.delete("/{event_id}/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    event_id: str,
    announcement_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> Response:
    try:
        removed = remove_announcement(db, event_id, announcement_id)
    except EventAnnouncementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
