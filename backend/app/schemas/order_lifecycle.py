from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.numeric import PositiveWholeQuantity
from app.schemas.purchase_order import PurchaseOrderResponse
from app.schemas.purchasing import PurchaseRequestResponse


class VendorOrderRequestCreate(BaseModel):
    store_number: str = Field(min_length=1, max_length=32)
    expected_delivery_date: date


class LifecycleLineWrite(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    quantity: PositiveWholeQuantity
    notes: str | None = Field(default=None, max_length=1000)


class VendorOrderRequestBulkCreate(BaseModel):
    store_numbers: list[str] = Field(min_length=1, max_length=500)
    expected_delivery_date: date
    line_items: list[LifecycleLineWrite] = Field(min_length=1, max_length=500)


class VendorOrderRequestDateUpdate(BaseModel):
    expected_delivery_date: date


class VendorPOResponse(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")
    eta: date | None = None
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_response(self) -> "VendorPOResponse":
        if self.action == "accept" and self.eta is None:
            raise ValueError("Accepted POs require an ETA")
        if self.action == "reject" and not (self.reason or "").strip():
            raise ValueError("Rejected POs require a reason")
        return self


class RequestDecision(BaseModel):
    action: str = Field(pattern="^(approve|cancel)$")
    reason: str | None = Field(default=None, max_length=1000)
    expected_delivery_date: date | None = None


class ReceivePOLine(BaseModel):
    quantity: PositiveWholeQuantity


class VendorEmailPreference(BaseModel):
    po_email_recipient: str | None = Field(default=None, max_length=320)


class GlobalETAUpdate(BaseModel):
    eta: date


class VendorPOIssue(BaseModel):
    action: str = Field(pattern="^(backorder|out_of_stock)$")
    line_id: int
    quantity: PositiveWholeQuantity
    eta: date | None = None
    substitute_product_code: str | None = Field(default=None, max_length=64)
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_issue(self) -> "VendorPOIssue":
        if self.action == "backorder" and self.eta is None:
            raise ValueError("Backordered units require an ETA")
        return self


class PurchasingPOChange(BaseModel):
    action: str = Field(pattern="^(cancel|add_model|remove_units|delay|expedite|request_eta)$")
    line_id: int | None = None
    product_code: str | None = Field(default=None, max_length=64)
    quantity: PositiveWholeQuantity | None = None
    requested_date: date | None = None
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_change(self) -> "PurchasingPOChange":
        if self.action == "add_model" and (not self.product_code or self.quantity is None):
            raise ValueError("Adding a model requires a model and quantity")
        if self.action == "remove_units" and (self.line_id is None or self.quantity is None):
            raise ValueError("Removing units requires a PO line and quantity")
        if self.action in {"delay", "expedite"} and self.requested_date is None:
            raise ValueError("Shipment date changes require a requested date")
        return self


class AttentionResponse(BaseModel):
    action: str = Field(pattern="^(accept|deny|acknowledge|confirm)$")
    eta: date | None = None
    note: str | None = Field(default=None, max_length=1000)


class POAttentionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    purchase_order_id: str
    initiated_by_side: str
    action_type: str
    status: str
    payload: dict
    reason: str | None
    response_note: str | None
    created_by: str
    responded_by: str | None
    created_at: datetime
    responded_at: datetime | None


class LifecycleRequestResponse(PurchaseRequestResponse):
    pass


class LifecyclePOResponse(PurchaseOrderResponse):
    vendor_eta: date | None
    vendor_response_at: datetime | None
    vendor_rejection_reason: str | None
    attention_items: list[POAttentionResponse]


class LifecycleSummary(BaseModel):
    active: list[LifecyclePOResponse]
    rejected: list[LifecyclePOResponse]
