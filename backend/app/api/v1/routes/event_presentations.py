import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission, user_has_permission
from app.auth.security import (
    create_presenter_token,
    create_projector_token,
    decode_presenter_token,
    decode_projector_token,
)
from app.db.session import get_db
from app.models.event_management import (
    EventBrandingAsset,
    EventProductSlide,
    EventProductSlideImage,
    EventProductSlideVendorLogo,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_presentation import (
    EventLiveAnalyticsResponse,
    EventPresentationAction,
    EventPresentationResponse,
    EventPresenterAccessResponse,
    EventProjectorAccessResponse,
)
from app.services.event_access_service import user_has_sub_event_access
from app.services.event_presentation_service import (
    EventPresentationError,
    control_presentation,
    get_live_analytics,
    get_presentation,
)
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(prefix="/event-presentations", tags=["event presentations"])
public_router = APIRouter(prefix="/public-event-presentations", tags=["public event projector"])
projector_token_header = APIKeyHeader(
    name="X-BTSP-Projector-Token",
    scheme_name="ProjectorAccessToken",
)
presenter_token_header = APIKeyHeader(
    name="X-BTSP-Presenter-Token",
    scheme_name="PresenterMonitorAccessToken",
)


def _validate_projector_access(
    db: Session,
    sub_event_id: str,
    projector_token: str,
) -> ManagedSubEvent:
    try:
        decode_projector_token(projector_token, sub_event_id)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Projector link is invalid or expired") from exc
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    event = db.get(ManagedEvent, sub_event.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=403, detail="This projector display is closed")
    return sub_event


def _validate_presenter_access(
    db: Session,
    sub_event_id: str,
    presenter_token: str,
) -> ManagedSubEvent:
    try:
        decode_presenter_token(presenter_token, sub_event_id)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Presenter link is invalid or expired") from exc
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    event = db.get(ManagedEvent, sub_event.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=403, detail="This presenter monitor is closed")
    return sub_event


@router.get("/{sub_event_id}/analytics", response_model=EventLiveAnalyticsResponse)
def read_live_analytics(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventLiveAnalyticsResponse:
    try:
        analytics = get_live_analytics(db, sub_event_id)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if analytics is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return analytics


@router.get("/{sub_event_id}", response_model=EventPresentationResponse)
def read_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventPresentationResponse:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    has_manage_access = user_has_permission(user, "events.manage")
    if not has_manage_access and not user_has_sub_event_access(
        db, sub_event.event_id, sub_event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is required")
    # The running presentation is projector-only. Attendees receive role-
    # specific live-event workspaces from the calendar instead.
    if not has_manage_access:
        raise HTTPException(
            status_code=403,
            detail="The live presentation is available only on the projector display",
        )
    try:
        return get_presentation(db, sub_event_id)  # type: ignore[return-value]
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{sub_event_id}/presenter", response_model=EventPresentationResponse)
def read_presenter_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventPresentationResponse:
    try:
        presentation = get_presentation(db, sub_event_id, include_presenter_details=True)
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return presentation


@router.post(
    "/{sub_event_id}/projector-access",
    response_model=EventProjectorAccessResponse,
)
def create_presentation_projector_access(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventProjectorAccessResponse:
    try:
        presentation = get_presentation(db, sub_event_id)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    event = db.get(ManagedEvent, presentation.event_id)
    if event is None or event.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=403, detail="This projector display is closed")
    projector_token, expires_at = create_projector_token(sub_event_id)
    return EventProjectorAccessResponse(
        projector_token=projector_token,
        expires_at=expires_at,
    )


@router.post(
    "/{sub_event_id}/presenter-access",
    response_model=EventPresenterAccessResponse,
)
def create_presentation_presenter_access(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventPresenterAccessResponse:
    try:
        presentation = get_presentation(db, sub_event_id, include_presenter_details=True)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    event = db.get(ManagedEvent, presentation.event_id)
    if event is None or event.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=403, detail="This presenter monitor is closed")
    presenter_token, expires_at = create_presenter_token(sub_event_id)
    return EventPresenterAccessResponse(
        presenter_token=presenter_token,
        expires_at=expires_at,
    )


@public_router.get("/{sub_event_id}", response_model=EventPresentationResponse)
def read_public_projector_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    projector_token: str = Depends(projector_token_header),
) -> EventPresentationResponse:
    _validate_projector_access(db, sub_event_id, projector_token)
    try:
        presentation = get_presentation(db, sub_event_id)
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return presentation


@public_router.get(
    "/{sub_event_id}/presenter-monitor",
    response_model=EventPresentationResponse,
)
def read_public_presenter_presentation(
    sub_event_id: str,
    db: Session = Depends(get_db),
    presenter_token: str = Depends(presenter_token_header),
) -> EventPresentationResponse:
    _validate_presenter_access(db, sub_event_id, presenter_token)
    try:
        presentation = get_presentation(db, sub_event_id, include_presenter_details=True)
    except EventPresentationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return presentation


@public_router.get("/{sub_event_id}/slides/{slide_id}/image")
def read_public_projector_slide_image(
    sub_event_id: str,
    slide_id: str,
    db: Session = Depends(get_db),
    projector_token: str = Depends(projector_token_header),
) -> Response:
    _validate_projector_access(db, sub_event_id, projector_token)
    slide = db.get(EventProductSlide, slide_id)
    if slide is None or slide.sub_event_id != sub_event_id:
        raise HTTPException(status_code=404, detail="Product image not found")
    image = db.get(EventProductSlideImage, slide_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Product image not found")
    return Response(
        image.content,
        media_type=image.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@public_router.get("/{sub_event_id}/slides/{slide_id}/vendor-logo")
def read_public_projector_vendor_logo(
    sub_event_id: str,
    slide_id: str,
    db: Session = Depends(get_db),
    projector_token: str = Depends(projector_token_header),
) -> Response:
    _validate_projector_access(db, sub_event_id, projector_token)
    slide = db.get(EventProductSlide, slide_id)
    if slide is None or slide.sub_event_id != sub_event_id or slide.status == "archived":
        raise HTTPException(status_code=404, detail="Vendor logo not found")
    logo = db.get(EventProductSlideVendorLogo, slide_id)
    if logo is None:
        raise HTTPException(status_code=404, detail="Vendor logo not found")
    return Response(
        logo.content,
        media_type=logo.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@public_router.get("/{sub_event_id}/presenter-monitor/slides/{slide_id}/image")
def read_public_presenter_slide_image(
    sub_event_id: str,
    slide_id: str,
    db: Session = Depends(get_db),
    presenter_token: str = Depends(presenter_token_header),
) -> Response:
    _validate_presenter_access(db, sub_event_id, presenter_token)
    slide = db.get(EventProductSlide, slide_id)
    if slide is None or slide.sub_event_id != sub_event_id or slide.status == "archived":
        raise HTTPException(status_code=404, detail="Product image not found")
    image = db.get(EventProductSlideImage, slide_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Product image not found")
    return Response(
        image.content,
        media_type=image.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@public_router.get("/{sub_event_id}/branding")
def read_public_projector_branding(
    sub_event_id: str,
    db: Session = Depends(get_db),
    projector_token: str = Depends(projector_token_header),
) -> Response:
    sub_event = _validate_projector_access(db, sub_event_id, projector_token)
    asset = db.get(EventBrandingAsset, sub_event.event_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Branding image not found")
    return Response(
        asset.content,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/{sub_event_id}/control", response_model=EventPresentationResponse)
async def post_presentation_control(
    sub_event_id: str,
    payload: EventPresentationAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventPresentationResponse:
    try:
        presentation = control_presentation(db, sub_event_id, payload.action, user.email)
    except EventPresentationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if presentation is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "presentation.changed")
    return presentation
