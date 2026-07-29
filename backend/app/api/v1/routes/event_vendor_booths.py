from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.event_management import EventVendorBooth
from app.models.identity import User
from app.schemas.catalog import CatalogVendorResponse
from app.schemas.event_vendor_booth import (
    EventOnlyVendorCreate,
    EventVendorBoothResponse,
    EventVendorBoothWrite,
)
from app.services.event_access_service import event_window_open_for_user
from app.services.event_vendor_booth_service import (
    EventVendorBoothError,
    create_event_only_vendor,
    list_available_vendors,
    list_event_booths,
    my_booths,
    save_booth,
    vendor_update_booth,
)

router = APIRouter(prefix="/event-vendor-booths", tags=["event vendor booths"])


@router.get("/{event_id}/available-vendors", response_model=list[CatalogVendorResponse])
def read_available_vendors(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
):
    vendors = list_available_vendors(db, event_id)
    if vendors is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return vendors


@router.post(
    "/{event_id}/event-only-vendors",
    response_model=CatalogVendorResponse,
    status_code=201,
)
def post_event_only_vendor(
    event_id: str,
    payload: EventOnlyVendorCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
):
    try:
        vendor = create_event_only_vendor(db, event_id, payload.name)
    except EventVendorBoothError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if vendor is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return vendor


@router.get("/mine", response_model=list[EventVendorBoothResponse])
def read_my_booths(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EventVendorBoothResponse]:
    return [
        booth
        for booth in my_booths(db, user)
        if event_window_open_for_user(db, booth.event_id, user.id)
    ]


@router.get("/{event_id}", response_model=list[EventVendorBoothResponse])
def read_booths(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventVendorBoothResponse]:
    booths = list_event_booths(db, event_id)
    if booths is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return booths


@router.post("/{event_id}", response_model=EventVendorBoothResponse)
def post_booth(
    event_id: str,
    payload: EventVendorBoothWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventVendorBoothResponse:
    try:
        booth = save_booth(db, event_id, payload, user.email)
    except EventVendorBoothError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return booth


@router.put("/mine/{booth_id}", response_model=EventVendorBoothResponse)
def put_my_booth(
    booth_id: str,
    payload: EventVendorBoothWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventVendorBoothResponse:
    booth_record = db.get(EventVendorBooth, booth_id)
    if booth_record is not None and not event_window_open_for_user(
        db, booth_record.event_id, user.id
    ):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")
    try:
        booth = vendor_update_booth(db, booth_id, payload, user)
    except EventVendorBoothError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Booth not found")
    return booth


@router.put("/{event_id}/{booth_id}", response_model=EventVendorBoothResponse)
def put_booth(
    event_id: str,
    booth_id: str,
    payload: EventVendorBoothWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventVendorBoothResponse:
    try:
        booth = save_booth(db, event_id, payload, user.email, booth_id)
    except EventVendorBoothError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if booth is None:
        raise HTTPException(status_code=404, detail="Booth not found")
    return booth
