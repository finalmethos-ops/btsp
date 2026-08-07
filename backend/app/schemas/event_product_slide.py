from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SlideStatus = Literal["draft", "ready", "archived"]
SlideType = Literal["product", "filler"]
FillerCategory = Literal[
    "trivia",
    "giveaway",
    "sponsorship",
    "special_thanks",
    "raffle",
    "full_screen_image",
]


class EventProductVariant(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_number: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    event_unit_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    standard_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    minimum_order_quantity: int = Field(default=1, ge=1)


class EventProductSlideWrite(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    slide_type: SlideType = "product"
    filler_category: FillerCategory | None = None
    catalog_product_code: str | None = Field(default=None, max_length=64)
    model_number: str | None = Field(default=None, min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    vendor_code: str | None = Field(default=None, min_length=1, max_length=64)
    category: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=10_000)
    specifications: str | None = Field(default=None, max_length=20_000)
    event_unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    standard_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    minimum_order_quantity: int = Field(default=1, ge=1)
    available_inventory: int | None = Field(default=None, ge=0)
    max_event_units: int | None = Field(default=None, ge=1)
    allow_waitlist: bool = False
    delivery_window_start: date | None = None
    delivery_window_end: date | None = None
    vendor_delivery_notes: str | None = Field(default=None, max_length=5000)
    presenter_notes: str | None = Field(default=None, max_length=5000)
    product_variants: list[EventProductVariant] = Field(default_factory=list, max_length=50)
    status: SlideStatus = "draft"

    @model_validator(mode="after")
    def valid_controls(self) -> "EventProductSlideWrite":
        if self.slide_type == "filler":
            if self.filler_category is None:
                raise ValueError("Filler slides require a category")
            if self.catalog_product_code or self.product_variants:
                raise ValueError("Filler slides cannot reference orderable products")
            return self
        required = {
            "model number": self.model_number,
            "vendor code": self.vendor_code,
            "event unit cost": self.event_unit_cost,
            "delivery window start": self.delivery_window_start,
            "delivery window end": self.delivery_window_end,
        }
        missing = [label for label, value in required.items() if value is None]
        if missing:
            raise ValueError(f"Product slides require {', '.join(missing)}")
        if self.delivery_window_end < self.delivery_window_start:
            raise ValueError("Delivery window end must be on or after its start")
        if (
            self.max_event_units is not None
            and self.available_inventory is not None
            and self.max_event_units > self.available_inventory
        ):
            raise ValueError("Maximum event units cannot exceed available inventory")
        variant_models = [variant.model_number.casefold() for variant in self.product_variants]
        if len(variant_models) != len(set(variant_models)):
            raise ValueError("Each product on a combined slide must have a unique model number")
        return self


class EventProductSlideResponse(EventProductSlideWrite):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    event_id: str
    sub_event_id: str
    position: int
    vendor_name: str | None = None
    has_image: bool = False
    created_by: str
    created_at: datetime


class EventProductSlideReorder(BaseModel):
    slide_ids: list[str] = Field(min_length=1, max_length=500)


class EventProductWebFillResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_number: str
    title: str
    summary: str
    source_url: str
    image_url: str | None = None


class EventProductImageImport(BaseModel):
    image_url: str = Field(min_length=10, max_length=2048)
