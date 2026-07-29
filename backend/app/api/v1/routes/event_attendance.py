from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_attendance import (
    EventAttendancePassLookup,
    EventAttendancePassLookupResponse,
    EventAttendancePassResponse,
    EventAttendanceRosterResponse,
    EventAttendanceUpdate,
)
from app.services.event_access_service import event_window_open_for_user
from app.services.event_attendance_service import (
    EventAttendanceError,
    attendance_roster,
    my_attendance_passes,
    update_attendance,
    update_attendance_by_pass_code,
)
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(prefix="/event-attendance", tags=["event attendance"])


@router.get("/mine", response_model=list[EventAttendancePassResponse])
def read_my_attendance_passes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EventAttendancePassResponse]:
    return [
        event_pass
        for event_pass in my_attendance_passes(db, user)
        if event_window_open_for_user(db, event_pass.event_id, user.id)
    ]


@router.get("/{sub_event_id}", response_model=EventAttendanceRosterResponse)
def read_attendance_roster(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventAttendanceRosterResponse:
    try:
        roster = attendance_roster(db, sub_event_id)
    except EventAttendanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if roster is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return roster


@router.put(
    "/{sub_event_id}/members/{membership_id}",
    response_model=EventAttendanceRosterResponse,
)
async def put_attendance(
    sub_event_id: str,
    membership_id: str,
    payload: EventAttendanceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventAttendanceRosterResponse:
    try:
        roster = update_attendance(db, sub_event_id, membership_id, payload.status, user.email)
    except EventAttendanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if roster is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "attendance.changed")
    return roster


@router.post(
    "/{sub_event_id}/pass-check-in",
    response_model=EventAttendancePassLookupResponse,
)
async def post_pass_check_in(
    sub_event_id: str,
    payload: EventAttendancePassLookup,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventAttendancePassLookupResponse:
    try:
        result = update_attendance_by_pass_code(
            db, sub_event_id, payload.pass_code, payload.status, user.email
        )
    except EventAttendanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "attendance.changed")
    return result
