import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.responses import content_disposition
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_any_permission, require_permission, user_has_permission
from app.db.session import get_db
from app.models.event_management import EventMembership, StoreLoadoutAssignment
from app.models.identity import User
from app.schemas.store_loadout import (
    StoreLoadoutAssignmentResponse,
    StoreLoadoutAssignmentWrite,
    StoreLoadoutEventResponse,
    StoreLoadoutEventWrite,
    StoreLoadoutFinalReviewWrite,
    StoreLoadoutItemAttachmentResponse,
    StoreLoadoutItemCheckinWrite,
    StoreLoadoutReassignmentWrite,
    StoreLoadoutRouteEstimateResponse,
    StoreLoadoutRouteRecalculateResponse,
    StoreLoadoutSignoffResponse,
    StoreLoadoutSignoffWrite,
    StoreLoadoutSummaryResponse,
    StoreLoadoutTeamWrite,
    StoreLoadoutVehicleStatusWrite,
)
from app.services.loadout_routing_service import (
    LoadoutRoutingError,
    estimate_store_route,
    recalculate_store_routes,
)
from app.services.spreadsheet_security import spreadsheet_safe_row
from app.services.store_loadout_service import (
    StoreLoadoutAccessError,
    StoreLoadoutError,
    assign_store_loadout_team,
    attach_store_loadout_item_file,
    auto_order_store_loadout,
    checkin_store_loadout_item,
    complete_store_loadout_final_review,
    configure_store_loadout,
    create_store_loadout_assignment,
    latest_store_loadout_signoff,
    list_store_loadout_assignments,
    mark_store_loadout_assignment_ready,
    my_store_loadout_assignments,
    reassign_store_loadout_inventory,
    release_store_loadout_assignment,
    sign_store_loadout_assignment,
    store_loadout_export_rows,
    store_loadout_item_attachment_content,
    store_loadout_packing_lists_pdf,
    store_loadout_summary,
    store_loadout_window_open,
    update_store_loadout_vehicle_status,
)

router = APIRouter(prefix="/store-loadout", tags=["store loadout"])


def _require_event_loadout_read(db: Session, event_id: str, user: User) -> None:
    if user_has_permission(user, "store_loadout.read") or user_has_permission(
        user, "store_loadout.manage"
    ):
        return
    assigned = db.scalar(
        select(EventMembership.id).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user.id,
            (
                EventMembership.loadout_role.in_(("team_lead", "dockmaster", "overseer"))
                | EventMembership.membership_type.in_(("team_lead", "dockmaster", "overseer"))
            ),
            EventMembership.is_active.is_(True),
        )
    )
    if assigned is None:
        raise HTTPException(status_code=403, detail="Store loadout access is not assigned")


@router.post(
    "/assignments/{assignment_id}/items/{item_id}/attachments",
    response_model=StoreLoadoutItemAttachmentResponse,
)
async def post_store_loadout_item_attachment(
    assignment_id: str,
    item_id: str,
    attachment_type: str = Query(default="photo"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"store_loadout.manage", "store_loadout.store.checkin"})
    ),
) -> StoreLoadoutItemAttachmentResponse:
    content = await file.read(8 * 1024 * 1024 + 1)
    try:
        attachment = attach_store_loadout_item_file(
            db,
            assignment_id,
            item_id,
            attachment_type,
            file.filename or "loadout-evidence",
            file.content_type or "application/octet-stream",
            content,
            user,
        )
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if attachment is None:
        raise HTTPException(status_code=404, detail="Store loadout item not found")
    return StoreLoadoutItemAttachmentResponse.model_validate(attachment)


@router.get("/assignments/{assignment_id}/items/{item_id}/attachments/{attachment_id}/content")
def get_store_loadout_item_attachment_content(
    assignment_id: str,
    item_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"store_loadout.manage", "store_loadout.store.checkin"})
    ),
) -> Response:
    try:
        attachment = store_loadout_item_attachment_content(
            db, assignment_id, item_id, attachment_id, user
        )
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if attachment is None:
        raise HTTPException(status_code=404, detail="Store loadout attachment not found")
    filename, content_type, content = attachment
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post(
    "/events/{event_id}/route-estimates/recalculate",
    response_model=StoreLoadoutRouteRecalculateResponse,
)
def recalculate_event_store_routes(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("store_loadout.manage")),
) -> StoreLoadoutRouteRecalculateResponse:
    return recalculate_store_routes(db, event_id)


@router.get(
    "/events/{event_id}/route-estimate/{store_number}",
    response_model=StoreLoadoutRouteEstimateResponse,
)
def read_store_route_estimate(
    event_id: str,
    store_number: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("store_loadout.manage")),
) -> StoreLoadoutRouteEstimateResponse:
    try:
        estimate = estimate_store_route(db, event_id, store_number)
    except LoadoutRoutingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if estimate is None:
        raise HTTPException(status_code=404, detail="Event or store not found")
    return estimate


def _enforce_store_loadout_window_for_assignment(
    db: Session,
    assignment_id: str,
    user: User,
) -> None:
    if user_has_permission(user, "store_loadout.manage"):
        return
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is not None and not store_loadout_window_open(db, assignment.event_id):
        raise HTTPException(status_code=403, detail="Store loadout is not currently open")


@router.get("/mine", response_model=list[StoreLoadoutAssignmentResponse])
def read_my_store_loadout_assignments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[StoreLoadoutAssignmentResponse]:
    return [
        assignment
        for assignment in my_store_loadout_assignments(db, user)
        if store_loadout_window_open(db, assignment.event_id)
    ]


@router.post(
    "/assignments/{assignment_id}/items/{item_id}/checkin",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_item_checkin(
    assignment_id: str,
    item_id: str,
    payload: StoreLoadoutItemCheckinWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    _enforce_store_loadout_window_for_assignment(db, assignment_id, user)
    try:
        assignment = checkin_store_loadout_item(db, assignment_id, item_id, payload, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout item not found")
    return assignment


@router.put(
    "/assignments/{assignment_id}/team",
    response_model=StoreLoadoutAssignmentResponse,
)
def put_store_loadout_assignment_team(
    assignment_id: str,
    payload: StoreLoadoutTeamWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    try:
        assignment = assign_store_loadout_team(db, assignment_id, payload, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.post(
    "/assignments/{assignment_id}/final-review",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_assignment_final_review(
    assignment_id: str,
    payload: StoreLoadoutFinalReviewWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    _enforce_store_loadout_window_for_assignment(db, assignment_id, user)
    try:
        assignment = complete_store_loadout_final_review(db, assignment_id, payload, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.post(
    "/assignments/{assignment_id}/ready",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_assignment_ready(
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"store_loadout.manage", "store_loadout.store.checkin"})
    ),
) -> StoreLoadoutAssignmentResponse:
    _enforce_store_loadout_window_for_assignment(db, assignment_id, user)
    try:
        assignment = mark_store_loadout_assignment_ready(db, assignment_id, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.post(
    "/assignments/{assignment_id}/sign",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_assignment_signoff(
    assignment_id: str,
    payload: StoreLoadoutSignoffWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"store_loadout.manage", "store_loadout.store.checkin"})
    ),
) -> StoreLoadoutAssignmentResponse:
    _enforce_store_loadout_window_for_assignment(db, assignment_id, user)
    try:
        assignment = sign_store_loadout_assignment(db, assignment_id, payload, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.post(
    "/assignments/{assignment_id}/release",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_assignment_release(
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    try:
        assignment = release_store_loadout_assignment(db, assignment_id, user)
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.put(
    "/assignments/{assignment_id}/vehicles/{vehicle_label}/status",
    response_model=StoreLoadoutAssignmentResponse,
)
def put_store_loadout_vehicle_status(
    assignment_id: str,
    vehicle_label: str,
    payload: StoreLoadoutVehicleStatusWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    try:
        assignment = update_store_loadout_vehicle_status(
            db, assignment_id, vehicle_label, payload, user
        )
    except StoreLoadoutAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.get(
    "/assignments/{assignment_id}/signoff",
    response_model=StoreLoadoutSignoffResponse | None,
)
def read_store_loadout_assignment_signoff(
    assignment_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("store_loadout.read")),
) -> StoreLoadoutSignoffResponse | None:
    return latest_store_loadout_signoff(db, assignment_id)


@router.put("/events/{event_id}", response_model=StoreLoadoutEventResponse)
def put_store_loadout_event(
    event_id: str,
    payload: StoreLoadoutEventWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("store_loadout.manage")),
) -> StoreLoadoutEventResponse:
    try:
        loadout = configure_store_loadout(db, event_id, payload, user.email)
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if loadout is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return loadout


@router.post(
    "/events/{event_id}/assignments",
    response_model=StoreLoadoutAssignmentResponse,
)
def post_store_loadout_assignment(
    event_id: str,
    payload: StoreLoadoutAssignmentWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("store_loadout.manage")),
) -> StoreLoadoutAssignmentResponse:
    try:
        assignment = create_store_loadout_assignment(db, event_id, payload, user.email)
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return assignment


@router.get(
    "/events/{event_id}/assignments",
    response_model=list[StoreLoadoutAssignmentResponse],
)
def read_store_loadout_assignments(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[StoreLoadoutAssignmentResponse]:
    _require_event_loadout_read(db, event_id, _user)
    assignments = list_store_loadout_assignments(db, event_id)
    if assignments is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return assignments


@router.post(
    "/events/{event_id}/auto-order",
    response_model=list[StoreLoadoutAssignmentResponse],
)
def post_store_loadout_auto_order(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("store_loadout.manage")),
) -> list[StoreLoadoutAssignmentResponse]:
    try:
        assignments = auto_order_store_loadout(db, event_id, user.email)
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignments is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return assignments


@router.put(
    "/assignments/{assignment_id}/reassign",
    response_model=StoreLoadoutAssignmentResponse,
)
def put_store_loadout_assignment_reassignment(
    assignment_id: str,
    payload: StoreLoadoutReassignmentWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoreLoadoutAssignmentResponse:
    try:
        assignment = reassign_store_loadout_inventory(db, assignment_id, payload, user.email)
    except StoreLoadoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if assignment is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return assignment


@router.get("/events/{event_id}/summary", response_model=StoreLoadoutSummaryResponse)
def read_store_loadout_summary(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> StoreLoadoutSummaryResponse:
    _require_event_loadout_read(db, event_id, _user)
    summary = store_loadout_summary(db, event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.get("/events/{event_id}/exports/{report_type}")
def export_store_loadout_report(
    event_id: str,
    report_type: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("store_loadout.export")),
) -> StreamingResponse:
    try:
        export = store_loadout_export_rows(db, event_id, report_type)
    except StoreLoadoutError as exc:
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
                f"store-loadout-{event_id}-{report_type}.csv"
            )
        },
    )


@router.get("/events/{event_id}/packing-lists-pdf")
def export_store_loadout_packing_lists_pdf(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("store_loadout.export")),
) -> Response:
    content = store_loadout_packing_lists_pdf(db, event_id, actor=user.email)
    if content is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                f"store-loadout-{event_id}-packing-lists.pdf"
            )
        },
    )


@router.get("/events/{event_id}/assignments/{assignment_id}/packing-list-pdf")
def export_store_loadout_assignment_packing_list_pdf(
    event_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("store_loadout.export")),
) -> Response:
    content = store_loadout_packing_lists_pdf(db, event_id, assignment_id, user.email)
    if content is None:
        raise HTTPException(status_code=404, detail="Store loadout assignment not found")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                f"store-loadout-{event_id}-assignment-{assignment_id}.pdf"
            )
        },
    )
