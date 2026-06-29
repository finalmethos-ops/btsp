from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CatalogVendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_code: str
    name: str
    is_active: bool


class CatalogProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    product_code: str
    vendor_code: str
    name: str
    model_number: str | None
    category: str | None
    brand: str | None
    unit_price: Decimal
    currency: str
    minimum_order_quantity: Decimal
    is_available: bool
    is_active: bool


class CatalogImportResponse(BaseModel):
    id: int
    filename: str
    status: str
    vendor_rows: int
    product_rows: int
    errors: list[dict[str, str | int]]
    imported_by: str
    created_at: datetime
    completed_at: datetime | None
