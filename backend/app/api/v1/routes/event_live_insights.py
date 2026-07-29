from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import user_has_permission
from app.db.session import get_db
from app.models.event_management import ManagedSubEvent
from app.models.identity import User
from app.schemas.event_live_insights import EventLiveInsightsResponse
from app.services.event_access_service import event_window_open_for_user
from app.services.event_live_insights_service import EventLiveInsightsError, live_insights

router = APIRouter(prefix="/event-live-insights", tags=["event live insights"])


@router.get("/{sub_event_id}", response_model=EventLiveInsightsResponse)
def get_live_insights(
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventLiveInsightsResponse:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if (
        sub_event is not None
        and not user_has_permission(user, "events.manage")
        and not event_window_open_for_user(db, sub_event.event_id, user.id)
    ):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")
    try:
        result = live_insights(db, sub_event_id, user)
    except EventLiveInsightsError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return result
