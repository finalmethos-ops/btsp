import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.responses import content_disposition
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_settlement import (
    EventSettlementExceptionResolutionWrite,
    EventSettlementExceptionWrite,
    EventSettlementSummaryResponse,
    EventSettlementWrite,
)
from app.services.event_settlement_service import (
    EventSettlementError,
    configure_event_settlement,
    create_event_settlement_exception,
    event_settlement_export_rows,
    event_settlement_summary,
    reopen_event_settlement_exception,
    resolve_event_settlement_exception,
)
from app.services.spreadsheet_security import spreadsheet_safe_row

router = APIRouter(prefix="/event-settlement", tags=["event settlement"])


@router.put("/events/{event_id}", response_model=EventSettlementSummaryResponse)
def put_event_settlement(
    event_id: str,
    payload: EventSettlementWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("event_settlement.manage")),
) -> EventSettlementSummaryResponse:
    try:
        summary = configure_event_settlement(db, event_id, payload, user.email)
    except EventSettlementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.get("/events/{event_id}/summary", response_model=EventSettlementSummaryResponse)
def read_event_settlement_summary(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("event_settlement.read")),
) -> EventSettlementSummaryResponse:
    summary = event_settlement_summary(db, event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.post(
    "/events/{event_id}/exceptions",
    response_model=EventSettlementSummaryResponse,
)
def post_event_settlement_exception(
    event_id: str,
    payload: EventSettlementExceptionWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("event_settlement.manage")),
) -> EventSettlementSummaryResponse:
    try:
        summary = create_event_settlement_exception(db, event_id, payload, user.email)
    except EventSettlementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.post(
    "/exceptions/{exception_id}/resolve",
    response_model=EventSettlementSummaryResponse,
)
def post_event_settlement_exception_resolution(
    exception_id: str,
    payload: EventSettlementExceptionResolutionWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("event_settlement.manage")),
) -> EventSettlementSummaryResponse:
    try:
        summary = resolve_event_settlement_exception(db, exception_id, payload, user.email)
    except EventSettlementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail="Settlement exception not found")
    return summary


@router.post(
    "/exceptions/{exception_id}/reopen",
    response_model=EventSettlementSummaryResponse,
)
def post_event_settlement_exception_reopen(
    exception_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("event_settlement.manage")),
) -> EventSettlementSummaryResponse:
    try:
        summary = reopen_event_settlement_exception(db, exception_id, user.email)
    except EventSettlementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail="Settlement exception not found")
    return summary


@router.get("/events/{event_id}/exports/{report_type}")
def export_event_settlement_report(
    event_id: str,
    report_type: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("event_settlement.export")),
) -> StreamingResponse:
    try:
        export = event_settlement_export_rows(db, event_id, report_type)
    except EventSettlementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if export is None:
        raise HTTPException(status_code=404, detail="Event not found")
    headers, rows = export
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(spreadsheet_safe_row(headers))
    writer.writerows(spreadsheet_safe_row(row) for row in rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": content_disposition(
                f"event-settlement-{event_id}-{report_type}.csv"
            )
        },
    )
