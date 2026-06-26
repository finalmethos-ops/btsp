from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str
    home_store_number: str | None = None
    region_code: str | None = None
    is_active: bool = True
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    display_name: str | None = None
    home_store_number: str | None = None
    region_code: str | None = None
    is_active: bool | None = None
    role_codes: list[str] | None = None


class UserAdminResponse(BaseModel):
    id: int
    email: str
    display_name: str
    home_store_number: str | None
    region_code: str | None
    is_active: bool
    roles: list[str]
    permissions: list[str]
