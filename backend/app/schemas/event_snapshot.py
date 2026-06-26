from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventSnapshotCreate(BaseModel):
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    payload: dict[str, Any]


class EventSnapshotResponse(EventSnapshotCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
