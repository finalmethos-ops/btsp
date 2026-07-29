import re
from hashlib import sha256
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.responses import content_disposition
from app.auth.permissions import require_any_permission, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_order_review import (
    EventOrderBackupArtifactResponse,
    EventOrderReleaseResponse,
    EventOrderReviewDecision,
    EventOrderReviewSummary,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.event_order_backup_service import (
    export_event_order_backup,
    get_archived_event_order_backup,
)
from app.services.event_order_review_service import (
    EventOrderReviewError,
    decide_order,
    export_review_csv,
    release_approved_orders,
    review_summary,
)
from app.services.snapshot_service import append_snapshot

router = APIRouter(prefix="/event-order-review", tags=["event order review"])


@router.get("/{event_id}", response_model=EventOrderReviewSummary)
def read_event_order_review(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventOrderReviewSummary:
    summary = review_summary(db, event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.put("/orders/{order_id}", response_model=EventOrderReviewSummary)
def put_event_order_decision(
    order_id: str,
    payload: EventOrderReviewDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventOrderReviewSummary:
    try:
        event_id = decide_order(db, order_id, payload, user.email)
    except EventOrderReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event_id is None:
        raise HTTPException(status_code=404, detail="Event order not found")
    return review_summary(db, event_id)  # type: ignore[return-value]


@router.post(
    "/{event_id}/release",
    response_model=EventOrderReleaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_event_order_release(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventOrderReleaseResponse:
    try:
        batch = release_approved_orders(db, event_id, user.email)
    except EventOrderReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if batch is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return batch


@router.get("/{event_id}/export.csv")
def download_event_order_review(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> Response:
    content = export_review_csv(db, event_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": content_disposition(f"event-{event_id}-orders.csv")},
    )


@router.get("/{event_id}/backup.xlsx")
def download_event_order_backup(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission({"events.manage", "event_settlement.export"})),
) -> StreamingResponse:
    export = export_event_order_backup(db, event_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event, content = export
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", event.name).strip("-") or "event"
    digest = sha256(content).hexdigest()
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="event.order_backup.exported",
            entity_type="managed_event",
            entity_id=event.id,
            actor=user.email,
            payload={
                "filename": f"{safe_name}-all-orders.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size_bytes": len(content),
                "sha256": digest,
            },
        ),
    )
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": content_disposition(f"{safe_name}-all-orders.xlsx"),
            "X-BTSP-Content-SHA256": digest,
        },
    )


@router.get("/{event_id}/archived-backup.xlsx")
def download_archived_event_order_backup(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_any_permission({"events.manage", "event_settlement.export"})),
) -> StreamingResponse:
    artifact = get_archived_event_order_backup(db, event_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Archived closeout backup not found")
    return StreamingResponse(
        BytesIO(artifact.content),
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": content_disposition(artifact.filename),
            "X-BTSP-Content-SHA256": artifact.sha256,
            "X-BTSP-Archived-Artifact-ID": artifact.id,
        },
    )


@router.get(
    "/{event_id}/archived-backup",
    response_model=EventOrderBackupArtifactResponse,
)
def read_archived_event_order_backup(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_any_permission({"events.manage", "event_settlement.export"})),
) -> EventOrderBackupArtifactResponse:
    artifact = get_archived_event_order_backup(db, event_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Archived closeout backup not found")
    return EventOrderBackupArtifactResponse.model_validate(artifact, from_attributes=True)
