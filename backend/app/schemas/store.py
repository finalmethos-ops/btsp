from datetime import datetime

from pydantic import BaseModel


class StoreBase(BaseModel):
    store_number: str
    name: str
    region_code: str
    district_code: str | None = None
    buying_group_code: str | None = None
    operating_company: str | None = None
    state_code: str | None = None
    timezone: str | None = None
    is_ordering_enabled: bool = True
    is_active: bool = True
    source_system: str = "official_store_database"
    source_updated_at: datetime | None = None


class StoreUpsert(StoreBase):
    pass


class StoreResponse(StoreBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegionScopeCheck(BaseModel):
    user_region_code: str
    target_store_numbers: list[str]


class RegionScopeResult(BaseModel):
    allowed: bool
    blocked_store_numbers: list[str]
