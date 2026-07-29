from pydantic import BaseModel, ConfigDict, Field


class VendorLiveProductMetric(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    slide_id: str
    position: int
    vendor_code: str
    vendor_name: str
    model_number: str
    name: str
    units_ordered: int
    committed_spend: str


class VendorLiveVendorMetric(BaseModel):
    vendor_code: str
    vendor_name: str
    units_ordered: int
    committed_spend: str


class EventLiveInsightsResponse(BaseModel):
    event_id: str
    event_name: str
    sub_event_id: str
    sub_event_name: str
    scope: str
    presentation_status: str
    ordering_status: str
    current_position: int | None
    total_slides: int
    sub_event_units: int
    sub_event_spend: str
    responding_entities: int
    entity_code: str | None = None
    franchise_sub_event_units: int = 0
    franchise_sub_event_spend: str = "0.00"
    vendor_code: str | None = None
    vendor_name: str | None = None
    vendor_sub_event_units: int = 0
    vendor_sub_event_spend: str = "0.00"
    slides_until_next_product: int | None = None
    next_vendor_code: str | None = None
    next_vendor_name: str | None = None
    vendor_totals: list[VendorLiveVendorMetric] = Field(default_factory=list)
    vendor_products: list[VendorLiveProductMetric] = Field(default_factory=list)
