from sqlalchemy.orm import Session

from app.models.event_snapshot import EventSnapshot
from app.schemas.event_snapshot import EventSnapshotCreate


def append_snapshot(db: Session, payload: EventSnapshotCreate) -> EventSnapshot:
    snapshot = EventSnapshot(**payload.model_dump())
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
