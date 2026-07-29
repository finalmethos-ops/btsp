from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    login_context: Literal["standard", "event"] = "standard"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: str | None = None


class VendorContextRequest(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=64)


class EventVendorContextRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=64)
    vendor_code: str = Field(min_length=1, max_length=64)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class VendorAccountResponse(BaseModel):
    vendor_code: str
    name: str


class CurrentUserResponse(BaseModel):
    email: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    workflows: list[str]
    vendor_code: str | None = None
    active_vendor_code: str | None = None
    vendor_accounts: list[VendorAccountResponse] = Field(default_factory=list)
    login_context: Literal["standard", "event"] = "standard"
    password_change_required: bool = False
