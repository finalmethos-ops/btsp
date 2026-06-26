from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_snapshot import EventSnapshot
from app.schemas.event_snapshot import EventSnapshotCreate


def append_snapshot(db: Session, payload: EventSnapshotCreate) -> EventSnapshot:
    snapshot = EventSnapshot(**payload.model_dump())
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def read_snapshots(
    db: Session,
    entity_type: str | None = None,
    entity_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[EventSnapshot]:
    statement = select(EventSnapshot)
    if entity_type is not None:
        statement = statement.where(EventSnapshot.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(EventSnapshot.entity_id == entity_id)
    if event_type is not None:
        statement = statement.where(EventSnapshot.event_type == event_type)
    statement = statement.order_by(EventSnapshot.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())
