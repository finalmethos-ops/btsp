from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.event_management import MembershipType


class EventCalendarEntryWrite(BaseModel):
    entry_type: Literal["text", "sub_event"]
    sub_event_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=255)
    visibility_categories: list[MembershipType] = Field(min_length=1, max_length=5)
    is_active: bool = True

    @model_validator(mode="after")
    def valid_entry(self) -> "EventCalendarEntryWrite":
        if self.ends_at <= self.starts_at:
            raise ValueError("Calendar entry end must be after its start")
        if self.entry_type == "sub_event" and not self.sub_event_id:
            raise ValueError("Linked calendar entries require a sub-event")
        if self.entry_type == "text":
            self.sub_event_id = None
        self.visibility_categories = sorted(set(self.visibility_categories))
        return self


class EventCalendarEntryResponse(BaseModel):
    id: str
    event_id: str
    event_name: str
    entry_type: Literal["text", "sub_event"]
    sub_event_id: str | None
    module_codes: list[str] = Field(default_factory=list)
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    location: str | None
    visibility_categories: list[MembershipType]
    is_active: bool
    sub_event_accessible: bool = True
    updated_at: datetime
