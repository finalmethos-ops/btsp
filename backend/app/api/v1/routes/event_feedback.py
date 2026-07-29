from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import user_has_permission
from app.db.session import get_db
from app.models.event_management import EventFeedbackResponse as FeedbackModel
from app.models.event_management import EventMembership, ManagedEvent
from app.models.identity import User
from app.schemas.event_feedback import EventFeedbackSummary, EventFeedbackWrite
from app.services.event_access_service import active_event_membership

router = APIRouter(prefix="/event-feedback", tags=["event feedback"])


@router.get("/{event_id}", response_model=EventFeedbackSummary)
def read_feedback(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventFeedbackSummary:
    if db.get(ManagedEvent, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if active_event_membership(db, event_id, user.id) is None and not user_has_permission(
        user, "events.manage"
    ):
        raise HTTPException(status_code=403, detail="Event membership required")
    rows = db.scalars(
        select(FeedbackModel)
        .where(FeedbackModel.event_id == event_id)
        .order_by(FeedbackModel.created_at.desc())
    ).all()
    eligible = (
        db.scalar(
            select(func.count())
            .select_from(EventMembership)
            .where(EventMembership.event_id == event_id, EventMembership.is_active.is_(True))
        )
        or 0
    )
    average = db.scalar(
        select(func.avg(FeedbackModel.rating)).where(FeedbackModel.event_id == event_id)
    )
    type_rows = db.execute(
        select(
            EventMembership.membership_type,
            func.count(FeedbackModel.id),
            func.avg(FeedbackModel.rating),
        )
        .join(FeedbackModel, FeedbackModel.user_id == EventMembership.user_id)
        .where(EventMembership.event_id == event_id, FeedbackModel.event_id == event_id)
        .group_by(EventMembership.membership_type)
        .order_by(EventMembership.membership_type)
    ).all()
    return EventFeedbackSummary(
        event_id=event_id,
        response_count=len(rows),
        eligible_attendee_count=eligible,
        response_rate=(len(rows) / eligible * 100) if eligible else 0,
        feedback_by_attendee_type=(
            [
                {
                    "attendee_type": attendee_type,
                    "response_count": count,
                    "average_rating": float(avg) if avg is not None else None,
                }
                for attendee_type, count, avg in type_rows
            ]
            if user_has_permission(user, "events.manage")
            else []
        ),
        average_rating=float(average) if average is not None else None,
        submitted_by_current_user=any(row.user_id == user.id for row in rows),
        responses=[
            {
                "id": row.id,
                "rating": row.rating,
                "comments": row.comments,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        if user_has_permission(user, "events.manage")
        else [],
    )


@router.put("/{event_id}", response_model=EventFeedbackSummary)
def submit_feedback(
    event_id: str,
    payload: EventFeedbackWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventFeedbackSummary:
    if db.get(ManagedEvent, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if active_event_membership(db, event_id, user.id) is None:
        raise HTTPException(status_code=403, detail="Event membership required")
    row = db.scalar(
        select(FeedbackModel).where(
            FeedbackModel.event_id == event_id, FeedbackModel.user_id == user.id
        )
    )
    if row is None:
        row = FeedbackModel(event_id=event_id, user_id=user.id)
        db.add(row)
    row.rating = payload.rating
    row.comments = payload.comments
    db.commit()
    return read_feedback(event_id, db, user)
