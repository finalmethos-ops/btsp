from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PurchaseReceiptLineCreate(BaseModel):
    purchase_order_line_id: int
    received_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    accepted_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    rejected_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    rejection_reason: str | None = Field(default=None, max_length=1000)
    lot_number: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_quantities(self) -> "PurchaseReceiptLineCreate":
        if self.accepted_quantity + self.rejected_quantity != self.received_quantity:
            raise ValueError("Accepted and rejected quantities must equal received quantity")
        if self.rejected_quantity > 0 and not self.rejection_reason:
            raise ValueError("Rejected quantity requires a reason")
        return self


class PurchaseReceiptCreate(BaseModel):
    purchase_order_id: str
    asn_id: str | None = None
    store_number: str = Field(min_length=1, max_length=32)
    external_receipt_id: str | None = Field(default=None, max_length=160)
    packing_slip_number: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    received_at: datetime
    lines: list[PurchaseReceiptLineCreate] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_lines(self) -> "PurchaseReceiptCreate":
        line_ids = [line.purchase_order_line_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Receipt contains duplicate purchase order lines")
        return self


class PurchaseReceiptLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_line_id: int
    asn_line_id: int | None
    product_code: str
    received_quantity: Decimal
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    rejection_reason: str | None
    lot_number: str | None


class ReceiptVarianceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receipt_id: str
    receipt_line_id: int
    variance_type: str
    severity: str
    expected_quantity: Decimal
    actual_quantity: Decimal
    difference_quantity: Decimal
    status: str
    detected_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_action: str | None
    resolution_note: str | None


class ReceiptVarianceResolution(BaseModel):
    action: str = Field(pattern="^(resolve|waive)$")
    note: str = Field(min_length=1, max_length=1000)


class PurchaseBackorderCreate(BaseModel):
    source_variance_id: str
    expected_at: datetime | None = None
    note: str = Field(min_length=1, max_length=1000)


class PurchaseBackorderAction(BaseModel):
    action: str = Field(pattern="^(receive|cancel|substitute)$")
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
    substitute_product_code: str | None = Field(default=None, max_length=64)
    note: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_action_details(self) -> "PurchaseBackorderAction":
        if self.action == "receive" and self.quantity is None:
            raise ValueError("Receive action requires a quantity")
        if self.action == "substitute" and not self.substitute_product_code:
            raise ValueError("Substitute action requires a product code")
        return self


class PurchaseBackorderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    quantity: Decimal | None
    note: str
    actor: str
    created_at: datetime


class PurchaseBackorderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    backorder_number: str
    source_variance_id: str
    purchase_order_id: str
    purchase_order_line_id: int
    store_number: str
    product_code: str
    original_quantity: Decimal
    fulfilled_quantity: Decimal
    outstanding_quantity: Decimal
    status: str
    expected_at: datetime | None
    substitute_product_code: str | None
    resolution_note: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    events: list[PurchaseBackorderEventResponse]


class PurchaseReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receipt_number: str
    purchase_order_id: str
    asn_id: str | None
    store_number: str
    external_receipt_id: str | None
    receipt_sha256: str
    status: str
    packing_slip_number: str | None
    notes: str | None
    received_at: datetime
    received_by: str
    created_at: datetime
    lines: list[PurchaseReceiptLineResponse]
    variances: list[ReceiptVarianceResponse] = Field(default_factory=list)
