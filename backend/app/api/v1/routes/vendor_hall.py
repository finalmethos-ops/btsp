from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.api.responses import content_disposition
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_any_permission, require_permission, user_has_permission
from app.db.session import get_db
from app.models.event_management import (
    EventMembership,
    VendorHallBooth,
    VendorHallSavedBooth,
)
from app.models.identity import User
from app.schemas.communication import InternalMessageCreate
from app.schemas.vendor_hall import (
    VendorHallBoothCheckinResponse,
    VendorHallBoothCheckinWrite,
    VendorHallBoothMapPositionWrite,
    VendorHallBoothResponse,
    VendorHallBoothStaffAssignmentWrite,
    VendorHallDirectoryMessageResponse,
    VendorHallDirectoryMessageWrite,
    VendorHallDirectoryResponse,
    VendorHallEventResponse,
    VendorHallEventWrite,
    VendorHallFloorMapResponse,
    VendorHallFloorMapStatusResponse,
    VendorHallFloorMapWrite,
    VendorHallInventoryImportResponse,
    VendorHallInventoryItemResponse,
    VendorHallInventoryItemWrite,
    VendorHallInventorySplitWrite,
    VendorHallInventoryStaffUpdate,
    VendorHallItemAttachmentResponse,
    VendorHallItemCheckinResponse,
    VendorHallItemCheckinWrite,
    VendorHallSummaryResponse,
)
from app.services.auth_service import user_role_codes
from app.services.communication_service import send_message
from app.services.event_access_service import active_event_membership, event_window_open_for_user
from app.services.vendor_hall_service import (
    MAX_FLOOR_MAP_BYTES,
    MAX_INVENTORY_ATTACHMENT_BYTES,
    MAX_INVENTORY_IMPORT_BYTES,
    VendorHallAccessError,
    VendorHallError,
    assign_booth_staff,
    attach_inventory_item_file,
    checkin_booth_inventory_item,
    complete_booth_checkin,
    configure_vendor_hall,
    create_booth_inventory_item,
    export_vendor_hall_report,
    force_close_vendor_hall,
    import_booth_inventory_csv,
    import_vendor_hall_floor_map_pdf,
    inventory_item_attachment_content,
    list_booth_inventory,
    list_vendor_hall_booths,
    mark_booth_ready_for_inspection,
    my_vendor_hall_booths,
    remove_inventory_item_attachment,
    save_vendor_hall_floor_map,
    split_booth_inventory_item,
    start_booth_checkin,
    submit_booth_inventory,
    sync_vendor_hall_booths,
    update_booth_inventory_item,
    update_booth_inventory_item_staff,
    update_booth_map_position,
    vendor_hall_floor_map_content,
    vendor_hall_floor_map_preview,
    vendor_hall_floor_map_status,
    vendor_hall_summary,
)

router = APIRouter(prefix="/vendor-hall", tags=["vendor hall"])
vendor_hall_access = require_any_permission(
    {
        "vendor_hall.read",
        "vendor_hall.manage",
        "vendor_hall.vendor.manage",
        "vendor_hall.staff.checkin",
    }
)


def _raise_access(exc: VendorHallAccessError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


def _enforce_vendor_window_for_booth(db: Session, booth_id: str, user: User) -> None:
    if user_has_permission(user, "vendor_hall.manage"):
        return
    booth = db.get(VendorHallBooth, booth_id)
    if booth is not None and not event_window_open_for_user(db, booth.event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")


@router.get("/mine", response_model=list[VendorHallBoothResponse])
def read_my_vendor_hall_booths(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VendorHallBoothResponse]:
    return [
        booth
        for booth in my_vendor_hall_booths(db, user)
        if event_window_open_for_user(db, booth.event_id, user.id)
    ]


@router.put("/events/{event_id}", response_model=VendorHallEventResponse)
def put_vendor_hall_event(
    event_id: str,
    payload: VendorHallEventWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.manage")),
) -> VendorHallEventResponse:
    try:
        hall = configure_vendor_hall(db, event_id, payload, user.email)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if hall is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return hall


@router.post("/events/{event_id}/force-close", response_model=VendorHallEventResponse)
def post_vendor_hall_force_close(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("system.admin")),
) -> VendorHallEventResponse:
    try:
        hall = force_close_vendor_hall(db, event_id, user.email)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if hall is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return hall


@router.post("/events/{event_id}/sync-booths", response_model=list[VendorHallBoothResponse])
def post_vendor_hall_booth_sync(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.manage")),
) -> list[VendorHallBoothResponse]:
    try:
        booths = sync_vendor_hall_booths(db, event_id, user.email)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booths is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return booths


@router.get("/events/{event_id}/booths", response_model=list[VendorHallBoothResponse])
def read_vendor_hall_booths(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.read")),
) -> list[VendorHallBoothResponse]:
    role_codes = set(user_role_codes(user))
    scoped_staff = (
        "EVENT_STAFF" in role_codes and not ({"ADMIN", "SYSTEM_ADMIN"} & role_codes)
    ) or (
        db.scalar(
            select(EventMembership.id).where(
                EventMembership.event_id == event_id,
                EventMembership.user_id == user.id,
                EventMembership.membership_type == "staff",
                EventMembership.is_active.is_(True),
            )
        )
        is not None
        and not ({"ADMIN", "SYSTEM_ADMIN"} & role_codes)
    )
    if "VENDOR" in role_codes or scoped_staff:
        return [booth for booth in my_vendor_hall_booths(db, user) if booth.event_id == event_id]
    booths = list_vendor_hall_booths(db, event_id)
    if booths is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return booths


@router.get("/events/{event_id}/summary", response_model=VendorHallSummaryResponse)
def read_vendor_hall_summary(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor_hall.read")),
) -> VendorHallSummaryResponse:
    summary = vendor_hall_summary(db, event_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return summary


@router.get("/events/{event_id}/exports/{report_type}")
def export_vendor_hall_csv(
    event_id: str,
    report_type: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor_hall.export")),
) -> Response:
    try:
        export = export_vendor_hall_report(db, event_id, report_type)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if export is None:
        raise HTTPException(status_code=404, detail="Event not found")
    filename, content = export
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.put("/events/{event_id}/floor-map", response_model=VendorHallFloorMapResponse)
def put_vendor_hall_floor_map(
    event_id: str,
    payload: VendorHallFloorMapWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.map.manage")),
) -> VendorHallFloorMapResponse:
    floor_map = save_vendor_hall_floor_map(db, event_id, payload, user)
    if floor_map is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return floor_map


@router.post("/events/{event_id}/floor-map/import-pdf", response_model=VendorHallFloorMapResponse)
async def post_vendor_hall_floor_map_pdf(
    event_id: str,
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.map.manage")),
) -> VendorHallFloorMapResponse:
    content = await file.read(MAX_FLOOR_MAP_BYTES + 1)
    try:
        floor_map = import_vendor_hall_floor_map_pdf(
            db,
            event_id,
            name,
            file.filename or "floor-plan.pdf",
            file.content_type or "application/pdf",
            content,
            user,
        )
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if floor_map is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return floor_map


@router.get("/events/{event_id}/floor-map/content")
def get_vendor_hall_floor_map_content(
    event_id: str,
    render: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor_hall.read")),
) -> Response:
    source = (
        vendor_hall_floor_map_preview(db, event_id)
        if render
        else vendor_hall_floor_map_content(db, event_id)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Floor plan PDF was not found")
    filename, content_type, content = source
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": content_disposition(filename, "inline")},
    )


@router.get("/events/{event_id}/floor-map", response_model=VendorHallFloorMapStatusResponse)
def read_vendor_hall_floor_map_status(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor_hall.read")),
) -> VendorHallFloorMapStatusResponse:
    floor_map = vendor_hall_floor_map_status(db, event_id)
    if floor_map is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return floor_map


@router.get("/events/{event_id}/directory", response_model=VendorHallDirectoryResponse)
def read_vendor_hall_directory(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VendorHallDirectoryResponse:
    if not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    floor_map = vendor_hall_floor_map_status(db, event_id)
    if floor_map is None:
        raise HTTPException(status_code=404, detail="Event not found")
    vendor_attendees: dict[str, list[str]] = {}
    membership = active_event_membership(db, event_id, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Event membership is required")
    saved_booths = {
        item.vendor_hall_booth_id: item
        for item in db.scalars(
            select(VendorHallSavedBooth).where(VendorHallSavedBooth.membership_id == membership.id)
        ).all()
    }
    for membership in db.scalars(
        select(EventMembership)
        .options(selectinload(EventMembership.user))
        .where(
            EventMembership.event_id == event_id,
            EventMembership.membership_type == "vendor",
            EventMembership.vendor_code.is_not(None),
            EventMembership.is_active.is_(True),
        )
    ).all():
        vendor_attendees.setdefault(membership.vendor_code or "", []).append(
            membership.user.display_name
        )
    return VendorHallDirectoryResponse(
        event_id=floor_map.event_id,
        event_name=floor_map.event_name,
        floor_map=floor_map.floor_map,
        booths=[
            {
                "id": booth.id,
                "booth_number": booth.booth_number,
                "booth_name": booth.booth_name,
                "vendor_name": booth.vendor_name,
                "floor_map_zone": booth.floor_map_zone,
                "map_x": booth.map_x,
                "map_y": booth.map_y,
                "map_width": booth.map_width,
                "map_height": booth.map_height,
                "attendees": sorted(set(vendor_attendees.get(booth.vendor_code, []))),
                "is_saved": booth.id in saved_booths,
                "is_visited": saved_booths.get(booth.id).visited_at is not None
                if booth.id in saved_booths
                else False,
            }
            for booth in floor_map.booths
        ],
    )


@router.post("/events/{event_id}/directory/booths/{booth_id}/saved", status_code=204)
def save_vendor_hall_directory_booth(
    event_id: str,
    booth_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    membership = active_event_membership(db, event_id, user.id)
    if membership is None or not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    booth = db.get(VendorHallBooth, booth_id)
    if booth is None or booth.event_id != event_id:
        raise HTTPException(status_code=404, detail="Vendor Hall booth not found")
    existing = db.scalar(
        select(VendorHallSavedBooth).where(
            VendorHallSavedBooth.membership_id == membership.id,
            VendorHallSavedBooth.vendor_hall_booth_id == booth_id,
        )
    )
    if existing is None:
        db.add(
            VendorHallSavedBooth(
                event_id=event_id,
                membership_id=membership.id,
                vendor_hall_booth_id=booth_id,
            )
        )
        db.commit()
    return Response(status_code=204)


@router.delete("/events/{event_id}/directory/booths/{booth_id}/saved", status_code=204)
def remove_vendor_hall_directory_booth(
    event_id: str,
    booth_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    membership = active_event_membership(db, event_id, user.id)
    if membership is None or not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    db.execute(
        delete(VendorHallSavedBooth).where(
            VendorHallSavedBooth.event_id == event_id,
            VendorHallSavedBooth.membership_id == membership.id,
            VendorHallSavedBooth.vendor_hall_booth_id == booth_id,
        )
    )
    db.commit()
    return Response(status_code=204)


@router.put(
    "/events/{event_id}/directory/booths/{booth_id}/visited",
    status_code=204,
)
def set_vendor_hall_directory_booth_visited(
    event_id: str,
    booth_id: str,
    visited: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    membership = active_event_membership(db, event_id, user.id)
    if membership is None or not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    saved = db.scalar(
        select(VendorHallSavedBooth).where(
            VendorHallSavedBooth.event_id == event_id,
            VendorHallSavedBooth.membership_id == membership.id,
            VendorHallSavedBooth.vendor_hall_booth_id == booth_id,
        )
    )
    if saved is None:
        raise HTTPException(status_code=404, detail="Save the booth before marking it visited")
    saved.visited_at = datetime.now(UTC) if visited else None
    db.commit()
    return Response(status_code=204)


@router.post(
    "/booths/{booth_id}/inventory/{item_id}/split",
    response_model=VendorHallInventoryItemResponse,
)
def post_inventory_item_split(
    booth_id: str,
    item_id: str,
    payload: VendorHallInventorySplitWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallInventoryItemResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        item = split_booth_inventory_item(db, booth_id, item_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Vendor hall inventory item not found")
    return item


@router.post(
    "/events/{event_id}/directory/booths/{booth_id}/messages",
    response_model=VendorHallDirectoryMessageResponse,
)
def message_vendor_hall_directory_booth(
    event_id: str,
    booth_id: str,
    payload: VendorHallDirectoryMessageWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VendorHallDirectoryMessageResponse:
    membership = active_event_membership(db, event_id, user.id)
    if membership is None or not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    booth = db.get(VendorHallBooth, booth_id)
    if booth is None or booth.event_id != event_id:
        raise HTTPException(status_code=404, detail="Vendor Hall booth not found")
    recipients = db.scalars(
        select(EventMembership)
        .options(selectinload(EventMembership.user))
        .where(
            EventMembership.event_id == event_id,
            EventMembership.membership_type == "vendor",
            EventMembership.vendor_code == booth.vendor_code,
            EventMembership.user_id != user.id,
            EventMembership.is_active.is_(True),
        )
    ).all()
    if not recipients:
        raise HTTPException(status_code=422, detail="No vendor representatives are available")
    for recipient in recipients:
        send_message(
            db,
            user.email,
            InternalMessageCreate(
                recipient_email=recipient.user.email,
                subject=payload.subject,
                body=(
                    f"Event booth inquiry for {booth.booth_name} "
                    f"(Booth {booth.booth_number or 'TBD'}):\n\n{payload.body}"
                ),
            ),
        )
    return VendorHallDirectoryMessageResponse(sent_count=len(recipients))


@router.get("/events/{event_id}/directory/content")
def get_vendor_hall_directory_content(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not event_window_open_for_user(db, event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is not currently available")
    source = vendor_hall_floor_map_preview(db, event_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Floor plan was not found")
    filename, content_type, content = source
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": content_disposition(filename, "inline")},
    )


@router.put(
    "/events/{event_id}/booths/{booth_id}/map-position",
    response_model=VendorHallBoothResponse,
)
def put_vendor_hall_booth_map_position(
    event_id: str,
    booth_id: str,
    payload: VendorHallBoothMapPositionWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.map.manage")),
) -> VendorHallBoothResponse:
    booth = update_booth_map_position(db, event_id, booth_id, payload, user)
    if booth is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return booth


@router.put(
    "/events/{event_id}/booths/{booth_id}/staff-assignment",
    response_model=VendorHallBoothResponse,
)
def put_vendor_hall_booth_staff_assignment(
    event_id: str,
    booth_id: str,
    payload: VendorHallBoothStaffAssignmentWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor_hall.manage")),
) -> VendorHallBoothResponse:
    try:
        booth = assign_booth_staff(db, event_id, booth_id, payload, user)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return booth


@router.get("/booths/{booth_id}/inventory", response_model=list[VendorHallInventoryItemResponse])
def read_booth_inventory(
    booth_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(vendor_hall_access),
) -> list[VendorHallInventoryItemResponse]:
    try:
        items = list_booth_inventory(db, booth_id, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if items is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return items


@router.post("/booths/{booth_id}/inventory", response_model=VendorHallInventoryItemResponse)
def post_booth_inventory_item(
    booth_id: str,
    payload: VendorHallInventoryItemWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallInventoryItemResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        item = create_booth_inventory_item(db, booth_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if item is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return item


@router.post(
    "/booths/{booth_id}/inventory/import",
    response_model=VendorHallInventoryImportResponse,
)
async def post_booth_inventory_import(
    booth_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallInventoryImportResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    content = await file.read(MAX_INVENTORY_IMPORT_BYTES + 1)
    try:
        inventory_import = import_booth_inventory_csv(
            db,
            booth_id,
            file.filename or "inventory.csv",
            file.content_type or "text/csv",
            content,
            user,
        )
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Inventory import must be UTF-8 CSV") from exc
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if inventory_import is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return inventory_import


@router.put(
    "/booths/{booth_id}/inventory/{item_id}",
    response_model=VendorHallInventoryItemResponse,
)
def put_booth_inventory_item(
    booth_id: str,
    item_id: str,
    payload: VendorHallInventoryItemWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallInventoryItemResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        item = update_booth_inventory_item(db, booth_id, item_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if item is None:
        raise HTTPException(status_code=404, detail="Vendor hall inventory item not found")
    return item


@router.put(
    "/booths/{booth_id}/inventory/{item_id}/staff-update",
    response_model=VendorHallInventoryItemResponse,
)
def put_booth_inventory_item_staff_update(
    booth_id: str,
    item_id: str,
    payload: VendorHallInventoryStaffUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.staff.checkin"})
    ),
) -> VendorHallInventoryItemResponse:
    try:
        item = update_booth_inventory_item_staff(db, booth_id, item_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if item is None:
        raise HTTPException(status_code=404, detail="Vendor hall inventory item not found")
    return item


@router.post(
    "/booths/{booth_id}/inventory/{item_id}/attachments",
    response_model=VendorHallItemAttachmentResponse,
)
async def post_inventory_item_attachment(
    booth_id: str,
    item_id: str,
    attachment_type: str = Query(default="photo"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallItemAttachmentResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    content = await file.read(MAX_INVENTORY_ATTACHMENT_BYTES + 1)
    try:
        attachment = attach_inventory_item_file(
            db,
            booth_id,
            item_id,
            attachment_type,
            file.filename or "attachment",
            file.content_type or "application/octet-stream",
            content,
            user,
        )
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if attachment is None:
        raise HTTPException(status_code=404, detail="Vendor hall inventory item not found")
    return attachment


@router.get("/booths/{booth_id}/inventory/{item_id}/attachments/{attachment_id}/content")
def get_inventory_item_attachment_content(
    booth_id: str,
    item_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        source = inventory_item_attachment_content(db, booth_id, item_id, attachment_id, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if source is None:
        raise HTTPException(status_code=404, detail="Inventory attachment not found")
    filename, content_type, content = source
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": content_disposition(filename),
            "Cache-Control": "private, no-store",
        },
    )


@router.delete(
    "/booths/{booth_id}/inventory/{item_id}/attachments/{attachment_id}",
    status_code=204,
)
def delete_inventory_item_attachment(
    booth_id: str,
    item_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> Response:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        removed = remove_inventory_item_attachment(db, booth_id, item_id, attachment_id, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Inventory attachment not found")
    return Response(status_code=204)


@router.post("/booths/{booth_id}/submit", response_model=VendorHallBoothResponse)
def post_booth_inventory_submission(
    booth_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallBoothResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        booth = submit_booth_inventory(db, booth_id, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if booth is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return booth


@router.post("/booths/{booth_id}/ready-for-inspection", response_model=VendorHallBoothResponse)
def post_booth_ready_for_inspection(
    booth_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.vendor.manage"})
    ),
) -> VendorHallBoothResponse:
    _enforce_vendor_window_for_booth(db, booth_id, user)
    try:
        booth = mark_booth_ready_for_inspection(db, booth_id, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return booth


@router.post("/booths/{booth_id}/checkin/start", response_model=VendorHallBoothCheckinResponse)
def post_booth_checkin_start(
    booth_id: str,
    payload: VendorHallBoothCheckinWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.staff.checkin"})
    ),
) -> VendorHallBoothCheckinResponse:
    try:
        checkin = start_booth_checkin(db, booth_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return checkin


@router.post(
    "/booths/{booth_id}/inventory/{item_id}/checkin",
    response_model=VendorHallItemCheckinResponse,
)
def post_inventory_item_checkin(
    booth_id: str,
    item_id: str,
    payload: VendorHallItemCheckinWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.staff.checkin"})
    ),
) -> VendorHallItemCheckinResponse:
    try:
        checkin = checkin_booth_inventory_item(db, booth_id, item_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    if checkin is None:
        raise HTTPException(status_code=404, detail="Vendor hall inventory item not found")
    return checkin


@router.post("/booths/{booth_id}/checkin/complete", response_model=VendorHallBoothResponse)
def post_booth_checkin_complete(
    booth_id: str,
    payload: VendorHallBoothCheckinWrite,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission({"vendor_hall.manage", "vendor_hall.staff.checkin"})
    ),
) -> VendorHallBoothResponse:
    try:
        booth = complete_booth_checkin(db, booth_id, payload, user)
    except VendorHallAccessError as exc:
        _raise_access(exc)
    except VendorHallError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Vendor hall booth not found")
    return booth
