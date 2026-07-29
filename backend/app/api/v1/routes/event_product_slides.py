from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission, user_has_permission
from app.db.session import get_db
from app.models.event_management import (
    EventProductSlide,
    EventProductSlideImage,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_product_slide import (
    EventProductImageImport,
    EventProductSlideReorder,
    EventProductSlideResponse,
    EventProductSlideWrite,
    EventProductWebFillResponse,
)
from app.services.event_access_service import user_has_sub_event_access
from app.services.event_product_slide_service import (
    EventProductSlideError,
    create_slide,
    delete_slide,
    list_slides,
    reorder_slides,
    save_slide_image,
    update_slide,
)
from app.services.event_product_web_fill_service import (
    EventProductWebFillError,
    download_public_image,
    search_product,
)

router = APIRouter(prefix="/event-product-slides", tags=["event product slides"])


@router.get("/web-fill", response_model=EventProductWebFillResponse)
def read_web_fill(
    model_number: str = Query(min_length=1, max_length=64),
    product_name: str | None = Query(default=None, max_length=255),
    _user: User = Depends(require_permission("events.manage")),
) -> EventProductWebFillResponse:
    try:
        return search_product(model_number, product_name)
    except EventProductWebFillError as exc:
        status_code = 503 if "requires BRAVE_SEARCH_API_KEY" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/sub-events/{sub_event_id}", response_model=list[EventProductSlideResponse])
def read_slides(
    sub_event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventProductSlideResponse]:
    try:
        slides = list_slides(db, sub_event_id)
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slides is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return slides


@router.post(
    "/sub-events/{sub_event_id}",
    response_model=EventProductSlideResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_slide(
    sub_event_id: str,
    payload: EventProductSlideWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventProductSlideResponse:
    try:
        slide = create_slide(db, sub_event_id, payload, user.email)
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slide is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return slide


@router.put("/{slide_id}", response_model=EventProductSlideResponse)
def put_slide(
    slide_id: str,
    payload: EventProductSlideWrite,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> EventProductSlideResponse:
    try:
        slide = update_slide(db, slide_id, payload)
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slide is None:
        raise HTTPException(status_code=404, detail="Product slide not found")
    return slide


@router.delete("/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_slide(
    slide_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> None:
    try:
        deleted = delete_slide(db, slide_id)
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if deleted is None:
        raise HTTPException(status_code=404, detail="Product slide not found")


@router.put("/sub-events/{sub_event_id}/order", response_model=list[EventProductSlideResponse])
def put_slide_order(
    sub_event_id: str,
    payload: EventProductSlideReorder,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventProductSlideResponse]:
    try:
        slides = reorder_slides(db, sub_event_id, payload.slide_ids)
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slides is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return slides


@router.post("/{slide_id}/image", response_model=EventProductSlideResponse)
async def post_slide_image(
    slide_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventProductSlideResponse:
    try:
        slide = save_slide_image(
            db,
            slide_id,
            file.filename or "product-image",
            file.content_type or "application/octet-stream",
            await file.read(8 * 1024 * 1024 + 1),
            user.email,
        )
    except EventProductSlideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slide is None:
        raise HTTPException(status_code=404, detail="Product slide not found")
    return slide


@router.post("/{slide_id}/image-from-web", response_model=EventProductSlideResponse)
def post_slide_image_from_web(
    slide_id: str,
    payload: EventProductImageImport,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventProductSlideResponse:
    try:
        content_type, content = download_public_image(payload.image_url)
        slide = save_slide_image(
            db,
            slide_id,
            "web-fill-product-image",
            content_type,
            content,
            user.email,
        )
    except (EventProductWebFillError, EventProductSlideError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if slide is None:
        raise HTTPException(status_code=404, detail="Product slide not found")
    return slide


@router.get("/{slide_id}/image")
def read_slide_image(
    slide_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    slide = db.get(EventProductSlide, slide_id)
    if slide is None:
        raise HTTPException(status_code=404, detail="Product slide not found")
    sub_event = db.get(ManagedSubEvent, slide.sub_event_id)
    if not user_has_permission(user, "events.manage") and not (
        sub_event and user_has_sub_event_access(db, slide.event_id, slide.sub_event_id, user.id)
    ):
        raise HTTPException(status_code=403, detail="Event access is required")
    image = db.get(EventProductSlideImage, slide_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Product image not found")
    return Response(
        image.content,
        media_type=image.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )
