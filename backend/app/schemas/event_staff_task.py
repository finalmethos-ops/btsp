from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskPriority = Literal["low", "normal", "high", "urgent"]
TaskStatus = Literal["open", "in_progress", "done", "blocked", "cancelled"]
TaskPhase = Literal["pre_event", "live_event", "post_event"]


class EventStaffTaskAttachmentResponse(BaseModel):
    id: str
    task_id: str
    filename: str
    content_type: str
    uploaded_by: str
    created_at: datetime


class EventStaffTaskWrite(BaseModel):
    assigned_membership_id: str
    sub_event_id: str | None = None
    vendor_hall_booth_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = "normal"
    status: TaskStatus = "open"
    task_phase: TaskPhase = "live_event"
    due_at: datetime | None = None


class EventStaffTaskStatusWrite(BaseModel):
    status: TaskStatus
    note: str | None = Field(default=None, max_length=2000)


class EventStaffTaskResponse(EventStaffTaskWrite):
    id: str
    event_id: str
    event_name: str
    sub_event_name: str | None
    vendor_hall_booth_name: str | None
    assigned_display_name: str
    assigned_email: str
    status_note: str | None
    completed_at: datetime | None
    completed_by: str | None
    attachments: list[EventStaffTaskAttachmentResponse] = Field(default_factory=list)
    updated_at: datetime
