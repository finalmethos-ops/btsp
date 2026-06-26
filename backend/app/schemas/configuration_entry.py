from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConfigEntryWrite(BaseModel):
    scope_type: str
    scope_key: str
    key: str
    value: dict[str, Any]
    description: str | None = None
    is_active: bool = True
    updated_by: str


class ConfigEntryResponse(ConfigEntryWrite):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfigEntryLookup(BaseModel):
    scope_type: str
    scope_key: str
    key: str
