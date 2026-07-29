from pydantic import BaseModel, Field


class AdminBootstrapRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    home_store_number: str | None = Field(default=None, max_length=32)
    region_code: str | None = Field(default=None, max_length=64)


class AdminBootstrapResponse(BaseModel):
    email: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    created: bool
