from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_snapshot import EventSnapshotCreate, EventSnapshotResponse
from app.services.snapshot_service import append_snapshot, read_snapshots

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.get("", response_model=list[EventSnapshotResponse])
def list_snapshots(
    entity_type: str | None = None,
    entity_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("snapshots.read")),
) -> list[EventSnapshotResponse]:
    return read_snapshots(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        limit=limit,
    )


@router.post("", response_model=EventSnapshotResponse)
def create_snapshot(
    payload: EventSnapshotCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> EventSnapshotResponse:
    return append_snapshot(db, payload)
