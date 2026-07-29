from datetime import datetime

from pydantic import BaseModel, Field


class EventFeedbackWrite(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: str | None = Field(default=None, max_length=5000)


class EventFeedbackSummary(BaseModel):
    event_id: str
    response_count: int
    eligible_attendee_count: int
    response_rate: float
    feedback_by_attendee_type: list[dict]
    average_rating: float | None
    submitted_by_current_user: bool
    responses: list[dict]


class EventFeedbackResponse(BaseModel):
    id: str
    rating: int
    comments: str | None
    created_at: datetime
