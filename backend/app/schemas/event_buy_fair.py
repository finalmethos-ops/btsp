from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order_lifecycle import LifecycleLineWrite
from app.schemas.purchasing import PurchaseRequestResponse


class EventBuyFairOrderCreate(BaseModel):
    requester_id: int = Field(gt=0)
    store_numbers: list[str] = Field(min_length=1, max_length=500)
    expected_delivery_date: date
    line_items: list[LifecycleLineWrite] = Field(min_length=1, max_length=500)


class EventBuyFairModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    product_code: str
    model_identifier: str
    name: str
    unit_price: Decimal
    currency: str
    minimum_order_quantity: Decimal
    is_booth_model: bool


class EventBuyFairStore(BaseModel):
    store_number: str
    name: str
    entity_code: str | None
    region_code: str
    city: str | None
    state_code: str | None


class EventBuyFairRequester(BaseModel):
    id: int
    display_name: str
    entity_code: str | None
    region_code: str | None


class EventBuyFairWorkspace(BaseModel):
    event_id: str
    event_name: str
    sub_event_id: str
    sub_event_name: str
    vendor_code: str
    models: list[EventBuyFairModel]
    stores: list[EventBuyFairStore]
    requesters: list[EventBuyFairRequester]
    orders: list[PurchaseRequestResponse]
    order_count: int
    total_units: Decimal
    total_volume: Decimal


class EventBuyFairSummary(BaseModel):
    event_id: str
    sub_event_id: str | None = None
    vendor_count: int
    order_count: int
    draft_count: int
    submitted_count: int
    total_units: Decimal
    total_volume: Decimal
    vendors: list["EventBuyFairVendorSummary"]
    orders: list["EventBuyFairOrderSummary"]


class EventBuyFairVendorSummary(BaseModel):
    vendor_code: str
    order_count: int
    draft_count: int
    submitted_count: int
    total_units: Decimal
    total_volume: Decimal


class EventBuyFairOrderSummary(BaseModel):
    id: str
    order_number: str
    vendor_code: str
    store_number: str
    requester_name: str | None = None
    requester_email: str | None = None
    requester_entity_code: str | None = None
    requester_region_code: str | None = None
    status: str
    expected_delivery_date: date | None
    total_units: Decimal
    total_volume: Decimal
    created_at: datetime
