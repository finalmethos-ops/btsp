from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EventPollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=10)
    slide_id: str | None = None
    show_results: bool = True

    @model_validator(mode="after")
    def unique_options(self) -> "EventPollCreate":
        normalized = [option.strip().casefold() for option in self.options]
        if any(not option for option in normalized):
            raise ValueError("Poll options cannot be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Poll options must be unique")
        return self


class EventPollStatusUpdate(BaseModel):
    status: Literal["open", "closed"]


class EventPollVoteCreate(BaseModel):
    option_id: str


class EventPollOptionResponse(BaseModel):
    id: str
    position: int
    label: str
    vote_count: int
    percentage: float


class EventPollResponse(BaseModel):
    id: str
    event_id: str
    sub_event_id: str
    slide_id: str | None
    question: str
    status: Literal["draft", "open", "closed"]
    show_results: bool
    total_votes: int
    selected_option_id: str | None
    options: list[EventPollOptionResponse]
    created_at: datetime
    opened_at: datetime | None
    closed_at: datetime | None
