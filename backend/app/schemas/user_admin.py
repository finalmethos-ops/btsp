from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    home_store_number: str | None = Field(default=None, max_length=32)
    region_code: str | None = Field(default=None, max_length=64)
    entity_code: str | None = Field(default=None, max_length=64)
    vendor_code: str | None = Field(default=None, max_length=64)
    vendor_codes: list[str] = Field(default_factory=list, max_length=100)
    is_active: bool = True
    password_change_required: bool = False
    role_codes: list[str] = Field(default_factory=list, max_length=100)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    home_store_number: str | None = Field(default=None, max_length=32)
    region_code: str | None = Field(default=None, max_length=64)
    entity_code: str | None = Field(default=None, max_length=64)
    vendor_code: str | None = Field(default=None, max_length=64)
    vendor_codes: list[str] | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    password_change_required: bool | None = None
    role_codes: list[str] | None = Field(default=None, max_length=100)


class UserAdminResponse(BaseModel):
    id: int
    email: str
    display_name: str
    home_store_number: str | None
    region_code: str | None
    entity_code: str | None
    vendor_code: str | None
    vendor_codes: list[str]
    is_active: bool
    password_change_required: bool
    roles: list[str]
    permissions: list[str]
