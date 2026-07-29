from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EventVendorBoothWrite(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=64)
    booth_name: str = Field(min_length=1, max_length=255)
    booth_number: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=320)
    website_url: str | None = Field(default=None, max_length=500)
    status: Literal["draft", "published"] = "draft"


class EventOnlyVendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class EventVendorBoothResponse(EventVendorBoothWrite):
    id: str
    event_id: str
    event_name: str
    vendor_name: str | None
    updated_at: datetime
