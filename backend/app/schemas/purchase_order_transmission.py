from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PurchaseOrderTransmissionChannel(StrEnum):
    MANUAL = "manual"
    SECURE_FILE = "secure_file"
    INTERNAL_EMAIL = "internal_email"


class PurchaseOrderTransmissionAction(StrEnum):
    RELEASE = "release"
    MARK_DELIVERED = "mark_delivered"
    MARK_FAILED = "mark_failed"
    CANCEL = "cancel"
    RETRY = "retry"


class PurchaseOrderTransmissionCreate(BaseModel):
    artifact_id: str
    channel: PurchaseOrderTransmissionChannel
    destination: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class PurchaseOrderTransmissionActionRequest(BaseModel):
    action: PurchaseOrderTransmissionAction
    reason: str | None = Field(default=None, max_length=1000)


class PurchaseOrderTransmissionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None
    actor: str
    created_at: datetime


class PurchaseOrderTransmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_order_id: str
    artifact_id: str
    channel: PurchaseOrderTransmissionChannel
    destination: str | None
    status: str
    notes: str | None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    events: list[PurchaseOrderTransmissionEventResponse]
