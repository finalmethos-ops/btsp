from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission, user_has_permission
from app.db.session import get_db
from app.models.event_management import ManagedSubEvent
from app.models.identity import User
from app.schemas.event_presentation import (
    EventLiveAnalyticsResponse,
    EventPresentationAction,
    EventPresentationResponse,
)
from app.services.event_access_service import user_has_sub_event_access
from app.services.event_presentation_service import (
    EventPresentationError,
    control_presentation,
    get_live_analytics,
    get_presentation,
)
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(prefix="/event-presentations", tags=["event presentations"])


@router.get("/{sub_event_id}/analytics", response_model=EventLiveAnalyticsResponse)
def read_live_analytics(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventLiveAnalyticsResponse:
    try:
        analytics = get_live_analytics(db, sub_event_id)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if analytics is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return analytics


@router.get("/{sub_event_id}", response_model=EventPresentationResponse)
def read_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventPresentationResponse:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    has_manage_access = user_has_permission(user, "events.manage")
    if not has_manage_access and not user_has_sub_event_access(
        db, sub_event.event_id, sub_event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is required")
    # The running presentation is projector-only. Attendees receive role-
    # specific live-event workspaces from the calendar instead.
    if not has_manage_access:
        raise HTTPException(
            status_code=403,
            detail="The live presentation is available only on the projector display",
        )
    try:
        return get_presentation(db, sub_event_id)  # type: ignore[return-value]
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{sub_event_id}/presenter", response_model=EventPresentationResponse)
def read_presenter_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventPresentationResponse:
    try:
        presentation = get_presentation(db, sub_event_id, include_presenter_details=True)
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return presentation


@router.post("/{sub_event_id}/control", response_model=EventPresentationResponse)
async def post_presentation_control(
    sub_event_id: str,
    payload: EventPresentationAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventPresentationResponse:
    try:
        presentation = control_presentation(db, sub_event_id, payload.action, user.email)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "presentation.changed")
    return presentation
