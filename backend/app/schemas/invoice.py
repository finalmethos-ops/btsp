from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VendorInvoiceLineCreate(BaseModel):
    line_number: int = Field(gt=0)
    purchase_order_line_id: int
    product_code: str = Field(min_length=1, max_length=64)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    extended_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=4)

    @model_validator(mode="after")
    def validate_extension(self) -> "VendorInvoiceLineCreate":
        if self.quantity * self.unit_price != self.extended_amount:
            raise ValueError("Invoice line extended amount must equal quantity times unit price")
        return self


class VendorInvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=160)
    vendor_code: str = Field(min_length=1, max_length=64)
    purchase_order_id: str
    invoice_date: datetime
    due_date: datetime | None = None
    currency: str = Field(min_length=3, max_length=3)
    subtotal: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    freight_total: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    tax_total: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    total: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    lines: list[VendorInvoiceLineCreate] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_totals(self) -> "VendorInvoiceCreate":
        if len({line.line_number for line in self.lines}) != len(self.lines):
            raise ValueError("Invoice line numbers must be unique")
        if len({line.purchase_order_line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Purchase order lines may appear only once per invoice")
        if sum((line.extended_amount for line in self.lines), Decimal("0")) != self.subtotal:
            raise ValueError("Invoice subtotal must equal the sum of line amounts")
        if self.subtotal + self.freight_total + self.tax_total != self.total:
            raise ValueError("Invoice total must equal subtotal, freight, and tax")
        return self


class InvoiceLineMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ordered_quantity: Decimal
    accepted_quantity: Decimal
    invoiced_quantity: Decimal
    quantity_difference: Decimal
    ordered_unit_price: Decimal
    invoiced_unit_price: Decimal
    price_difference: Decimal
    status: str
    matched_at: datetime


class VendorInvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_number: int
    purchase_order_line_id: int
    product_code: str
    quantity: Decimal
    unit_price: Decimal
    extended_amount: Decimal
    match: InvoiceLineMatchResponse


class VendorInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    vendor_code: str
    purchase_order_id: str
    invoice_sha256: str
    invoice_date: datetime
    due_date: datetime | None
    currency: str
    subtotal: Decimal
    freight_total: Decimal
    tax_total: Decimal
    total: Decimal
    status: str
    received_by: str
    created_at: datetime
    lines: list[VendorInvoiceLineResponse]
