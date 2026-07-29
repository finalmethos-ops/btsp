from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.event_product_slide import EventProductSlideResponse


class EventEntityOrderWrite(BaseModel):
    quantity: int = Field(ge=1)
    variant_quantities: dict[str, int] = Field(default_factory=dict, max_length=50)

    @model_validator(mode="after")
    def valid_quantities(self) -> "EventEntityOrderWrite":
        if any(quantity < 0 for quantity in self.variant_quantities.values()):
            raise ValueError("Variant quantities cannot be negative")
        return self


class EventEntityOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slide_id: str
    entity_code: str
    quantity: int
    requested_delivery_start: date
    requested_delivery_end: date
    unit_cost: Decimal
    total_cost: Decimal
    status: Literal["confirmed", "waitlisted"]
    variant_quantities: dict[str, int] = Field(default_factory=dict)
    submitted_at: datetime
    updated_at: datetime


class EventOrderingWorkspaceResponse(BaseModel):
    event_id: str
    event_name: str
    sub_event_id: str
    sub_event_name: str
    entity_code: str
    ordering_status: Literal["open", "closed"]
    ordering_opened_at: datetime | None = None
    presentation_status: Literal["idle", "live", "ended"]
    current_slide: EventProductSlideResponse | None
    existing_order: EventEntityOrderResponse | None
    units_remaining: int | None
    entity_sub_event_spend: Decimal = Decimal("0.00")


class EventOrderingAssignmentResponse(BaseModel):
    event_id: str
    event_name: str
    sub_event_id: str
    sub_event_name: str
    starts_at: datetime
    ends_at: datetime
    location: str
    entity_code: str
