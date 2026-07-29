from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventOrderReviewDecision(BaseModel):
    decision: Literal["approve", "reject", "revise"]
    revised_quantity: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_decision(self) -> "EventOrderReviewDecision":
        if self.decision == "revise" and self.revised_quantity is None:
            raise ValueError("Revised quantity is required")
        if self.decision in {"reject", "revise"} and not (self.reason or "").strip():
            raise ValueError("A reason is required for rejection or revision")
        return self


class EventOrderVariantLine(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_number: str
    product_name: str
    quantity: int
    unit_cost: Decimal
    total_cost: Decimal


class EventOrderPurchasingLink(BaseModel):
    purchase_request_id: str
    order_number: str
    status: str


class EventOrderReviewItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    order_id: str
    sub_event_name: str
    entity_code: str
    vendor_code: str
    model_number: str
    product_name: str
    quantity: int
    unit_cost: Decimal
    total_cost: Decimal
    requested_delivery_start: date
    requested_delivery_end: date
    live_status: str
    review_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    variant_lines: list[EventOrderVariantLine] = Field(default_factory=list)
    purchasing_requests: list[EventOrderPurchasingLink] = Field(default_factory=list)


class EventOrderReviewSummary(BaseModel):
    event_id: str
    event_name: str
    pending: int
    approved: int
    rejected: int
    released: int
    approved_units: int
    approved_spend: Decimal
    items: list[EventOrderReviewItem]


class EventOrderReleaseResponse(BaseModel):
    batch_id: str
    event_id: str
    order_count: int
    vendor_count: int
    entity_count: int
    total_units: int
    total_spend: Decimal
    purchase_request_count: int = 0
    status: str
    created_at: datetime


class EventOrderBackupArtifactResponse(BaseModel):
    id: str
    event_id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_by: str
    created_at: datetime
