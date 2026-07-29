from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.numeric import NonNegativeCurrencyAmount


class CatalogVendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_code: str
    name: str
    is_active: bool


class CatalogVendorCreate(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
    name: str = Field(min_length=1, max_length=255)


class CatalogVendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class CatalogProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    product_code: str
    vendor_code: str
    name: str
    model_number: str | None
    department: str | None
    product_category_code: str | None
    brand: str | None
    is_clump: bool
    part_of_clump: bool
    cost_effective_start_date: date | None
    cost_status: str
    unit_price: Decimal
    currency: str
    minimum_order_quantity: Decimal
    moq_rule_id: int | None
    is_available: bool
    is_active: bool

    @computed_field
    @property
    def model_identifier(self) -> str:
        return self.model_number or self.product_code


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


class VendorModelUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    model_number: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=128)
    product_category_code: str | None = Field(default=None, max_length=128)
    brand: str | None = Field(default=None, max_length=128)
    is_clump: bool | None = None
    part_of_clump: bool | None = None
    cost_effective_start_date: date | None = None
    cost_status: str | None = Field(default=None, min_length=1, max_length=32)
    unit_price: NonNegativeCurrencyAmount | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    moq_rule_id: int | None = None
    is_available: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def required_values_cannot_be_null(self) -> "VendorModelUpdate":
        required = {
            "model_number",
            "name",
            "unit_price",
            "currency",
            "is_available",
            "is_active",
        }
        null_fields = sorted(
            field for field in required & self.model_fields_set if getattr(self, field) is None
        )
        if null_fields:
            raise ValueError(f"Fields may not be null: {', '.join(null_fields)}")
        return self


class CatalogProductCostHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_code: str
    vendor_code: str
    unit_price: Decimal
    currency: str
    effective_from: datetime
    effective_to: datetime | None
    changed_by: str
    source: str


class VendorModelImportResponse(BaseModel):
    filename: str
    created: int
    updated: int
    unchanged: int
    total_rows: int


class VendorMOQRuleWrite(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    threshold_type: str = Field(pattern="^(unit_quantity|order_amount)$")
    threshold_value: NonNegativeCurrencyAmount
    is_active: bool = True


class VendorMOQRuleResponse(VendorMOQRuleWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contributor_rule_ids: list[int] = Field(default_factory=list)


class VendorMOQCombinationWrite(BaseModel):
    contributor_rule_ids: list[int] = Field(default_factory=list)


class VendorStateExclusions(BaseModel):
    state_codes: list[str] = Field(default_factory=list)


class ModelCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department: str
    product_category_code: str
    status: str
