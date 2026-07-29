from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_closeout_insights import EventCloseoutInsightsResponse
from app.services.event_closeout_insights_service import (
    EventCloseoutInsightsError,
    event_closeout_insights,
)

router = APIRouter(prefix="/event-closeout-insights", tags=["event closeout insights"])


@router.get("/{event_id}", response_model=EventCloseoutInsightsResponse)
def read_event_closeout_insights(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventCloseoutInsightsResponse:
    try:
        result = event_closeout_insights(db, event_id, user)
    except EventCloseoutInsightsError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result
