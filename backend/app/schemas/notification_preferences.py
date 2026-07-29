from pydantic import BaseModel, Field


class NotificationPreferenceWrite(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = True
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class NotificationPreferenceResponse(NotificationPreferenceWrite):
    user_id: int
