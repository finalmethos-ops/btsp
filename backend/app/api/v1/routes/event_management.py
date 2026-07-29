from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_login_context
from app.auth.permissions import require_permission, user_has_permission
from app.db.session import get_db
from app.models.event_management import EventBrandingAsset, EventVenueMapAsset
from app.models.identity import User
from app.schemas.event_management import (
    SETUP_EVENT_MODULES,
    EventAccountDirectoryResponse,
    EventCancellationWrite,
    EventMembershipCreate,
    EventMembershipLoadoutRoleUpdate,
    EventMembershipRoleUpdate,
    EventModuleResponse,
    EventResponse,
    EventSubEventRegistrationWrite,
    EventVendorMembershipUpdate,
    EventWrite,
    SubEventModulesWrite,
    SubEventWrite,
)
from app.services.event_access_service import event_window_open_for_user
from app.services.event_management_service import (
    EventManagementError,
    add_membership,
    add_sub_event,
    assign_membership_sub_events,
    cancel_event,
    create_event,
    get_event,
    list_active_events,
    list_archived_events,
    list_event_account_directory,
    list_member_events,
    publish_event,
    remove_event,
    remove_sub_event,
    save_branding,
    save_venue_map,
    update_event,
    update_membership_loadout_role,
    update_membership_role,
    update_membership_vendors,
    update_sub_event,
    update_sub_event_modules,
)

router = APIRouter(prefix="/events", tags=["event management"])


@router.get("/modules", response_model=list[EventModuleResponse])
def read_event_modules(
    _user: User = Depends(get_current_user),
) -> list[EventModuleResponse]:
    return [EventModuleResponse(code=code, name=name) for code, name in SETUP_EVENT_MODULES.items()]


@router.get("/account-directory", response_model=list[EventAccountDirectoryResponse])
def read_event_account_directory(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventAccountDirectoryResponse]:
    return list_event_account_directory(db)


@router.get("/mine", response_model=list[EventResponse])
def read_my_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
) -> list[EventResponse]:
    # The standard administration workspace may preview all active events,
    # while the event portal must remain scoped to the events the administrator
    # is actually attending.
    if user_has_permission(user, "events.manage") and login_context != "event":
        return (
            # Event-session administrators need to preview and test future
            # active events before opening day. Draft and published events are
            # included; completed/cancelled events remain archived.
            list_active_events(db)
        )
    return [
        event
        for event in list_member_events(db, user.id)
        if event.status in {"draft", "published"}
        and event_window_open_for_user(db, event.id, user.id)
    ]


@router.get("", response_model=list[EventResponse])
def read_events(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventResponse]:
    return list_active_events(db)


@router.get("/archive", response_model=list[EventResponse])
def read_archived_events(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventResponse]:
    return list_archived_events(db)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def post_event(
    payload: EventWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        return create_event(db, payload, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{event_id}", response_model=EventResponse)
def put_event(
    event_id: str,
    payload: EventWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = update_event(db, event_id, payload)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/{event_id}/cancel", response_model=EventResponse)
def post_cancel_event(
    event_id: str,
    payload: EventCancellationWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = cancel_event(db, event_id, payload, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/{event_id}/publish", response_model=EventResponse)
def post_publish_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = publish_event(db, event_id, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> Response:
    try:
        removed = remove_event(db, event_id, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Event not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{event_id}/sub-events", response_model=EventResponse)
def post_sub_event(
    event_id: str,
    payload: SubEventWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = add_sub_event(db, event_id, payload)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put(
    "/{event_id}/memberships/{membership_id}/role",
    response_model=EventResponse,
)
def put_membership_role(
    event_id: str,
    membership_id: str,
    payload: EventMembershipRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    event = update_membership_role(db, event_id, membership_id, payload, user.email)
    if event is None:
        raise HTTPException(status_code=404, detail="Event membership not found")
    return event


@router.put(
    "/{event_id}/memberships/{membership_id}/loadout-role",
    response_model=EventResponse,
)
def put_membership_loadout_role(
    event_id: str,
    membership_id: str,
    payload: EventMembershipLoadoutRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    event = update_membership_loadout_role(db, event_id, membership_id, payload, user.email)
    if event is None:
        raise HTTPException(status_code=404, detail="Event membership not found")
    return event


@router.put(
    "/{event_id}/sub-events/{sub_event_id}/modules",
    response_model=EventResponse,
)
def put_sub_event_modules(
    event_id: str,
    sub_event_id: str,
    payload: SubEventModulesWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = update_sub_event_modules(db, event_id, sub_event_id, payload)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return event


@router.put("/{event_id}/sub-events/{sub_event_id}", response_model=EventResponse)
def put_sub_event(
    event_id: str,
    sub_event_id: str,
    payload: SubEventWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = update_sub_event(db, event_id, sub_event_id, payload)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return event


@router.delete(
    "/{event_id}/sub-events/{sub_event_id}",
    response_model=EventResponse,
)
def delete_sub_event(
    event_id: str,
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = remove_sub_event(db, event_id, sub_event_id, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return event


@router.post("/{event_id}/memberships", response_model=EventResponse)
def post_membership(
    event_id: str,
    payload: EventMembershipCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = add_membership(db, event_id, payload)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put(
    "/{event_id}/memberships/{membership_id}/sub-events",
    response_model=EventResponse,
)
def put_membership_sub_events(
    event_id: str,
    membership_id: str,
    payload: EventSubEventRegistrationWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = assign_membership_sub_events(db, event_id, membership_id, payload, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event membership not found")
    return event


@router.put(
    "/{event_id}/memberships/{membership_id}/vendors",
    response_model=EventResponse,
)
def put_membership_vendors(
    event_id: str,
    membership_id: str,
    payload: EventVendorMembershipUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = update_membership_vendors(db, event_id, membership_id, payload, user.email)
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event membership not found")
    return event


@router.post("/{event_id}/branding", response_model=EventResponse)
async def post_branding(
    event_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = save_branding(
            db,
            event_id,
            file.filename or "event-branding",
            file.content_type or "application/octet-stream",
            await file.read(5 * 1024 * 1024 + 1),
            user.email,
        )
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/branding")
def read_branding(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if get_event(db, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if not user_has_permission(user, "events.manage") and not event_window_open_for_user(
        db, event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is required")
    asset = db.get(EventBrandingAsset, event_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Branding image not found")
    return Response(
        asset.content,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/{event_id}/venue-map", response_model=EventResponse)
async def post_venue_map(
    event_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventResponse:
    try:
        event = save_venue_map(
            db,
            event_id,
            file.filename or "event-venue-map",
            file.content_type or "application/octet-stream",
            await file.read(10 * 1024 * 1024 + 1),
            user.email,
        )
    except EventManagementError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/venue-map")
def read_venue_map(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if get_event(db, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if not user_has_permission(user, "events.manage") and not event_window_open_for_user(
        db, event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is required")
    asset = db.get(EventVenueMapAsset, event_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Venue map not found")
    return Response(
        asset.content,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )
