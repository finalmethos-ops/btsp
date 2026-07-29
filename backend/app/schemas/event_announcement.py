from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.event_management import MembershipType


class EventAnnouncementWrite(BaseModel):
    sub_event_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10_000)
    severity: Literal["info", "important", "urgent"] = "info"
    visibility_categories: list[MembershipType] = Field(min_length=1, max_length=5)
    publishes_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def valid_window(self) -> "EventAnnouncementWrite":
        if self.expires_at and self.expires_at <= self.publishes_at:
            raise ValueError("Announcement expiration must be after publication")
        self.visibility_categories = sorted(set(self.visibility_categories))
        return self


class EventAnnouncementResponse(EventAnnouncementWrite):
    id: str
    event_id: str
    event_name: str
    sub_event_name: str | None
    updated_at: datetime
