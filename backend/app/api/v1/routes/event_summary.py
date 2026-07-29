from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_summary import EventSummaryResponse
from app.services.event_summary_service import EventSummaryError, event_summary

router = APIRouter(prefix="/event-summary", tags=["event summary"])


@router.get("/{event_id}", response_model=EventSummaryResponse)
def read_event_summary(
    event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> EventSummaryResponse:
    try:
        result = event_summary(db, event_id, user)
    except EventSummaryError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Event was not found")
    return result
