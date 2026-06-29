from datetime import datetime
from enum import StrEnum
from string import Formatter
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class RecipientStrategy(StrEnum):
    ACTOR = "actor"
    WORKFLOW_ROLE = "workflow_role"
    PERMISSION_HOLDERS = "permission_holders"
    REGION_ADMINS = "region_admins"
    STORE_USERS = "store_users"
    STATIC_RECIPIENTS = "static_recipients"


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class NotificationTemplateCreate(BaseModel):
    template_code: str = Field(min_length=2, max_length=160, pattern=r"^[A-Z0-9_.-]+$")
    workflow_code: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    channel: NotificationChannel
    subject_template: str = Field(min_length=1, max_length=500)
    body_template: str = Field(min_length=1, max_length=20000)
    recipient_strategy: RecipientStrategy
    recipient_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("subject_template", "body_template")
    @classmethod
    def safe_placeholders(cls, value: str) -> str:
        _validate_template_placeholders(value)
        return value

    @model_validator(mode="after")
    def validate_recipient_config(self) -> "NotificationTemplateCreate":
        _validate_recipient_config(self.recipient_strategy, self.recipient_config)
        return self


class NotificationTemplateUpdate(BaseModel):
    workflow_code: str | None = None
    event_type: str | None = None
    channel: NotificationChannel | None = None
    subject_template: str | None = None
    body_template: str | None = None
    recipient_strategy: RecipientStrategy | None = None
    recipient_config: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("subject_template", "body_template")
    @classmethod
    def safe_placeholders(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_template_placeholders(value)
        return value


def _validate_template_placeholders(value: str) -> None:
    for _, field_name, format_spec, conversion in Formatter().parse(value):
        if field_name is None:
            continue
        if (
            not field_name
            or not field_name.replace("_", "a").isalnum()
            or not field_name[0].isalpha()
        ):
            raise ValueError("Template placeholders must be simple names")
        if format_spec or conversion:
            raise ValueError("Template conversions and format specifications are not supported")


def _validate_recipient_config(
    strategy: RecipientStrategy, recipient_config: dict[str, Any]
) -> None:
    keys = {
        RecipientStrategy.STATIC_RECIPIENTS: {"recipients"},
        RecipientStrategy.WORKFLOW_ROLE: {"role_codes"},
        RecipientStrategy.PERMISSION_HOLDERS: {"permission_codes"},
        RecipientStrategy.REGION_ADMINS: {"role_codes"},
        RecipientStrategy.ACTOR: set(),
        RecipientStrategy.STORE_USERS: set(),
    }[strategy]
    if set(recipient_config) - keys:
        raise ValueError("Recipient configuration contains unsupported fields")
    for key, value in recipient_config.items():
        if not isinstance(value, list) or not value or len(value) > 100:
            raise ValueError(f"Recipient configuration must provide a non-empty list: {key}")
        if not all(isinstance(item, str) and 0 < len(item) <= 320 for item in value):
            raise ValueError(f"Recipient configuration contains invalid values: {key}")


class NotificationTemplateResponse(NotificationTemplateCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationEmitInput(BaseModel):
    workflow_code: str
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    context: dict[str, Any] = Field(default_factory=dict)


class NotificationEventResponse(BaseModel):
    notification_id: int = Field(validation_alias="id")
    template_code: str
    workflow_code: str
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    channel: NotificationChannel
    recipient_strategy: RecipientStrategy
    resolved_recipients: list[str]
    subject: str
    body: str
    status: NotificationStatus
    error_message: str | None
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}
