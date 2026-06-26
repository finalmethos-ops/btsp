from pydantic import BaseModel


class AdminBootstrapRequest(BaseModel):
    email: str
    display_name: str
    password: str
    home_store_number: str | None = None
    region_code: str | None = None


class AdminBootstrapResponse(BaseModel):
    email: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    created: bool
