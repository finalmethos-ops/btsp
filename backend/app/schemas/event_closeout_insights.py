from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class EventCloseoutInsightsResponse(BaseModel):
    event_id: str
    event_name: str
    status: str
    vendor_hall_status: str | None = None
    vendor_hall_closeout_ready: bool | None = None
    readiness_percentage: Decimal
    order_total: int
    order_released: int
    approved_units: int
    approved_spend: Decimal
    loadout_assignment_total: int
    loadout_released: int
    open_exception_count: int
    feedback_response_count: int
    feedback_eligible_attendee_count: int
    feedback_response_rate: Decimal
    feedback_average_rating: Decimal | None
    order_to_loadout_rate: Decimal
    approved_at: datetime | None
    closed_at: datetime | None
