from pydantic import BaseModel


class EventSummaryRow(BaseModel):
    sub_event_id: str
    sub_event_name: str
    order_count: int
    units: int
    spend: str


class EventSummaryBreakdown(BaseModel):
    code: str
    order_count: int
    units: int
    spend: str
    average_order_spend: str


class EventSummaryResponse(BaseModel):
    event_id: str
    event_name: str
    scope: str
    vendor_code: str | None = None
    entity_code: str | None = None
    region_code: str | None = None
    total_order_count: int
    total_units: int
    total_spend: str
    sub_events: list[EventSummaryRow]
    vendors: list[EventSummaryBreakdown]
    entities: list[EventSummaryBreakdown]
    departments: list[EventSummaryBreakdown]
