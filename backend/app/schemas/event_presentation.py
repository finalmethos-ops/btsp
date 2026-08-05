from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.event_product_slide import (
    EventProductSlideResponse,
    FillerCategory,
    SlideType,
)

PresentationAction = Literal["start", "previous", "next", "open", "close", "end"]


class EventPresentationAction(BaseModel):
    action: PresentationAction


class EventPresentationQueueItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    position: int
    slide_type: SlideType
    filler_category: FillerCategory | None = None
    model_number: str | None = None
    name: str
    presenter_notes: str | None = None


class EventProjectorAccessResponse(BaseModel):
    projector_token: str
    expires_at: datetime


class EventPresentationResponse(BaseModel):
    sub_event_id: str
    event_id: str
    event_name: str
    event_theme_primary_color: str = "#07142c"
    event_theme_accent_color: str = "#ffd400"
    event_has_branding: bool = False
    sub_event_name: str
    status: Literal["idle", "live", "ended"]
    ordering_status: Literal["open", "closed"]
    ordering_opened_at: datetime | None = None
    current_slide: EventProductSlideResponse | None
    total_slides: int
    current_position: int | None
    total_units_ordered: int = 0
    total_combined_spend: str = "0.00"
    sub_event_units_ordered: int = 0
    sub_event_combined_spend: str = "0.00"
    presenter_notes: str | None = None
    slide_queue: list[EventPresentationQueueItem] = Field(default_factory=list)
    updated_at: datetime | None


class EventLiveEntityOrder(BaseModel):
    entity_code: str
    quantity: int
    total_cost: str
    status: str
    updated_at: datetime


class EventLiveAnalyticsResponse(BaseModel):
    sub_event_id: str
    current_slide_id: str | None
    assigned_entities: int
    responding_entities: int
    confirmed_entities: int
    waitlisted_entities: int
    entities_remaining: int
    confirmed_units: int
    confirmed_spend: str
    waitlisted_units: int
    orders: list[EventLiveEntityOrder]
