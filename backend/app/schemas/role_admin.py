from pydantic import BaseModel, Field, field_validator


class PermissionAdminResponse(BaseModel):
    code: str
    description: str


class RoleAdminCreate(BaseModel):
    code: str = Field(min_length=2, max_length=128, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=255)
    workflow_code: str | None = Field(default=None, max_length=64)
    permission_codes: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("permission_codes")
    @classmethod
    def unique_permissions(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("permission_codes must not contain duplicates")
        return value


class RoleAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    workflow_code: str | None = Field(default=None, max_length=64)
    permission_codes: list[str] | None = Field(default=None, max_length=200)

    @field_validator("permission_codes")
    @classmethod
    def unique_permissions(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("permission_codes must not contain duplicates")
        return value


class RoleAdminResponse(BaseModel):
    id: int
    code: str
    name: str
    workflow_code: str | None
    is_system_role: bool
    permission_codes: list[str]
    user_count: int
