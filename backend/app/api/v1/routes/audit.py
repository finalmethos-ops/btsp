from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.audit_reporting import AuditEventPage, AuditSummaryResponse
from app.services.audit_reporting_service import (
    audit_summary,
    export_audit_csv,
    query_audit_events,
)

router = APIRouter(prefix="/audit", tags=["audit reporting"])


def _validate_dates(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from >= date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be earlier than date_to",
        )


@router.get("/events", response_model=AuditEventPage)
def read_audit_events(
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=1000000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("snapshots.read")),
) -> AuditEventPage:
    _validate_dates(date_from, date_to)
    return query_audit_events(
        db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=AuditSummaryResponse)
def read_audit_summary(
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("snapshots.read")),
) -> AuditSummaryResponse:
    _validate_dates(date_from, date_to)
    return audit_summary(
        db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/export")
def export_audit_events(
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit.export")),
) -> Response:
    _validate_dates(date_from, date_to)
    content = export_audit_csv(
        db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="btsp-audit.csv"'},
    )
