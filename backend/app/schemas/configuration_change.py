from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfigurationChangeCreate(BaseModel):
    scope_type: str = Field(min_length=1, max_length=64)
    scope_key: str = Field(min_length=1, max_length=128)
    key: str = Field(min_length=1, max_length=160)
    proposed_value: dict[str, Any]
    description: str | None = Field(default=None, max_length=500)


class ConfigurationChangeDecision(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ConfigurationChangeResponse(ConfigurationChangeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    requested_by: str
    decided_by: str | None
    decision_note: str | None
    created_at: datetime
    decided_at: datetime | None
