from datetime import datetime

from pydantic import BaseModel

from app.schemas.event_snapshot import EventSnapshotResponse


class AuditEventPage(BaseModel):
    items: list[EventSnapshotResponse]
    total: int
    limit: int
    offset: int


class AuditCountMetric(BaseModel):
    key: str
    count: int


class AuditSummaryResponse(BaseModel):
    total: int
    date_from: datetime | None
    date_to: datetime | None
    event_types: list[AuditCountMetric]
    entity_types: list[AuditCountMetric]
    actors: list[AuditCountMetric]
