from datetime import datetime

from pydantic import BaseModel, Field


class StoreBase(BaseModel):
    store_number: str = Field(pattern=r"^\d{4}$")
    name: str
    region_code: str
    operating_company: str | None = None
    entity_code: str | None = None
    purchasing_program: str | None = None
    regional_manager_name: str | None = None
    owner_operator_name: str | None = None
    general_manager_name: str | None = None
    manager_email: str | None = None
    address_line1: str | None = None
    city: str | None = None
    state_code: str | None = None
    postal_code: str | None = None
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


class StoreDirectoryOptions(BaseModel):
    entities: list[str]
    purchasing_programs: list[str]
    regions: list[str]
    entity_regions: dict[str, list[str]]


class POStoreFilterEntity(BaseModel):
    entity_code: str
    regions: list[str]


class POStoreFilterOptions(BaseModel):
    entities: list[POStoreFilterEntity]


class EntityRegionWrite(BaseModel):
    entity_code: str = Field(min_length=1, max_length=64)
    region_code: str = Field(min_length=1, max_length=64)


class EntityRegionResponse(EntityRegionWrite):
    model_config = {"from_attributes": True}
