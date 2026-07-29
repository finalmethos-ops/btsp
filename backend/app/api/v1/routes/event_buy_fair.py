import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.responses import content_disposition
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.event_management import ManagedSubEvent
from app.models.identity import User
from app.schemas.event_buy_fair import (
    EventBuyFairOrderCreate,
    EventBuyFairSummary,
    EventBuyFairWorkspace,
)
from app.schemas.order_lifecycle import LifecycleLineWrite, VendorOrderRequestDateUpdate
from app.schemas.purchasing import PurchaseRequestResponse
from app.services.event_access_service import event_window_open_for_user
from app.services.event_buy_fair_service import (
    EventBuyFairError,
    buy_fair_workspace,
    cancel_buy_fair_order,
    create_buy_fair_orders,
    event_buy_fair_export_rows,
    event_buy_fair_summary,
    require_buy_fair_order,
    sub_event_buy_fair_export_rows,
    sub_event_buy_fair_summary,
)
from app.services.order_lifecycle_service import (
    OrderLifecycleError,
    remove_request_line,
    submit_vendor_request,
    update_vendor_request_date,
    write_request_line,
)
from app.services.spreadsheet_security import spreadsheet_safe_row

router = APIRouter(prefix="/event-buy-fair", tags=["event vendor buy fair"])


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _enforce_event_window(db: Session, sub_event_id: str, user: User) -> None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is not None and not event_window_open_for_user(db, sub_event.event_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Event access is outside the scheduled window",
        )


@router.get("/events/{event_id}/summary", response_model=EventBuyFairSummary)
def read_event_summary(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
):
    summary = event_buy_fair_summary(db, event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Event was not found")
    return summary


@router.get("/events/{event_id}/export")
def export_event_orders(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> StreamingResponse:
    result = event_buy_fair_export_rows(db, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Event was not found")
    event, rows = result
    buffer = StringIO()
    csv.writer(buffer).writerows(spreadsheet_safe_row(row) for row in rows)
    filename = f"{event.slug}-vendor-buy-fair-orders.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.get("/sub-events/{sub_event_id}/summary", response_model=EventBuyFairSummary)
def read_sub_event_summary(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
):
    summary = sub_event_buy_fair_summary(db, sub_event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Sub-event was not found")
    return summary


@router.get("/sub-events/{sub_event_id}/export")
def export_sub_event_orders(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> StreamingResponse:
    result = sub_event_buy_fair_export_rows(db, sub_event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Sub-event was not found")
    event, sub_event, rows = result
    buffer = StringIO()
    csv.writer(buffer).writerows(spreadsheet_safe_row(row) for row in rows)
    filename = f"{event.slug}-{sub_event.id}-vendor-buy-fair-orders.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.get("/{sub_event_id}", response_model=EventBuyFairWorkspace)
def read_workspace(
    sub_event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        return buy_fair_workspace(db, sub_event_id, user)
    except EventBuyFairError as exc:
        raise _error(exc) from exc


@router.post(
    "/{sub_event_id}/orders", response_model=list[PurchaseRequestResponse], status_code=201
)
def create_orders(
    sub_event_id: str,
    payload: EventBuyFairOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        return create_buy_fair_orders(db, sub_event_id, payload, user)
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc


@router.patch(
    "/{sub_event_id}/orders/{request_id}/expected-delivery", response_model=PurchaseRequestResponse
)
def update_date(
    sub_event_id: str,
    request_id: str,
    payload: VendorOrderRequestDateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        request = require_buy_fair_order(db, sub_event_id, request_id, user)
        return update_vendor_request_date(db, request, payload.expected_delivery_date, user.email)
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc


@router.put("/{sub_event_id}/orders/{request_id}/lines", response_model=PurchaseRequestResponse)
def add_line(
    sub_event_id: str,
    request_id: str,
    payload: LifecycleLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        return write_request_line(
            db, require_buy_fair_order(db, sub_event_id, request_id, user), payload, user.email
        )
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc


@router.delete(
    "/{sub_event_id}/orders/{request_id}/lines/{line_id}", response_model=PurchaseRequestResponse
)
def delete_line(
    sub_event_id: str,
    request_id: str,
    line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        return remove_request_line(
            db, require_buy_fair_order(db, sub_event_id, request_id, user), line_id, user.email
        )
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc


@router.post("/{sub_event_id}/orders/{request_id}/submit", response_model=PurchaseRequestResponse)
def submit_order(
    sub_event_id: str,
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_event_window(db, sub_event_id, user)
    try:
        return submit_vendor_request(
            db, require_buy_fair_order(db, sub_event_id, request_id, user), user.email
        )
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc


@router.delete("/{sub_event_id}/orders/{request_id}", status_code=204)
def delete_order(
    sub_event_id: str,
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    _enforce_event_window(db, sub_event_id, user)
    try:
        cancel_buy_fair_order(
            db, require_buy_fair_order(db, sub_event_id, request_id, user), user.email
        )
    except (EventBuyFairError, OrderLifecycleError) as exc:
        raise _error(exc) from exc
    return Response(status_code=204)
