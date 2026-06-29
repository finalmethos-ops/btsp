from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PurchaseOrderGenerateRequest(BaseModel):
    purchase_request_ids: list[str] = Field(min_length=1, max_length=100)


class PurchaseOrderSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purchase_request_id: str
    store_number: str


class PurchaseOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_request_id: str
    source_line_id: int
    store_number: str
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    freight_amount: Decimal
    tax_amount: Decimal
    extended_amount: Decimal
    notes: str | None


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    po_number: str
    workflow_code: str
    vendor_code: str
    status: str
    currency: str
    subtotal: Decimal
    freight_total: Decimal
    tax_total: Decimal
    total: Decimal
    created_by: str
    created_at: datetime
    updated_at: datetime
    sources: list[PurchaseOrderSourceResponse]
    lines: list[PurchaseOrderLineResponse]


class PurchaseOrderSeedResponse(BaseModel):
    seeded_count: int
