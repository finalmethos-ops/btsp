from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.numeric import NonNegativeCurrencyAmount, PositiveWholeQuantity


class PurchaseRequestCreate(BaseModel):
    workflow_code: str
    store_number: str = Field(min_length=1, max_length=32)
    vendor_code: str = Field(min_length=1, max_length=64)
    context: dict[str, Any] = Field(default_factory=dict)


class PurchaseRequestUpdate(BaseModel):
    store_number: str | None = Field(default=None, min_length=1, max_length=32)
    vendor_code: str | None = Field(default=None, min_length=1, max_length=64)
    context: dict[str, Any] | None = None
    expected_revision: int | None = Field(default=None, ge=1)


class PurchaseLineWrite(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    quantity: PositiveWholeQuantity
    freight_amount: NonNegativeCurrencyAmount = Decimal("0")
    tax_amount: NonNegativeCurrencyAmount = Decimal("0")
    notes: str | None = Field(default=None, max_length=1000)


class PurchaseLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    product_code: str
    model_identifier: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    freight_amount: Decimal
    tax_amount: Decimal
    extended_amount: Decimal
    notes: str | None


class PurchaseRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    workflow_code: str
    workflow_instance_id: int | None
    store_number: str
    vendor_code: str
    status: str
    currency: str
    subtotal: Decimal
    freight_total: Decimal
    tax_total: Decimal
    total: Decimal
    expected_delivery_date: date | None
    context: dict[str, Any]
    revision: int
    expires_at: datetime | None
    cloned_from_id: str | None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    line_items: list[PurchaseLineResponse]


class PurchaseValidationIssue(BaseModel):
    code: str
    field: str | None = None
    message: str


class PurchaseValidationResult(BaseModel):
    ready: bool
    errors: list[PurchaseValidationIssue]
    warnings: list[PurchaseValidationIssue]


class DraftExpirationResponse(BaseModel):
    expired_count: int
