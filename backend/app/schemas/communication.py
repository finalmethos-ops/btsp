from datetime import datetime

from pydantic import BaseModel, Field


class InternalMessageCreate(BaseModel):
    recipient_email: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    reply_to_message_id: int | None = Field(default=None, ge=1)


class InternalMessageResponse(BaseModel):
    id: int
    conversation_id: str
    sender_email: str
    recipient_email: str
    subject: str
    body: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageRecipient(BaseModel):
    email: str
    display_name: str
