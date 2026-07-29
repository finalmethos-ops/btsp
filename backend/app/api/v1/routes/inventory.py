from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.inventory import (
    InventoryLedgerEntryCreate,
    InventoryLedgerEntryResponse,
    InventoryPositionResponse,
    InventoryReservationCreate,
    InventoryReservationResponse,
    InventoryTransferCreate,
    InventoryTransferResponse,
)
from app.services.inventory_service import (
    InventoryError,
    create_reservation,
    position,
    post_entry,
    post_transfer,
    release_reservation,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post(
    "/ledger", response_model=InventoryLedgerEntryResponse, status_code=status.HTTP_201_CREATED
)
def create_entry(
    payload: InventoryLedgerEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.manage")),
) -> InventoryLedgerEntryResponse:
    if user.home_store_number and payload.store_number != user.home_store_number:
        raise HTTPException(status_code=403, detail="Store access denied")
    return InventoryLedgerEntryResponse.model_validate(post_entry(db, payload, user.email))


@router.get("/position", response_model=InventoryPositionResponse)
def read_position(
    product_code: str,
    store_number: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.read")),
) -> InventoryPositionResponse:
    if user.home_store_number and store_number != user.home_store_number:
        raise HTTPException(status_code=403, detail="Store access denied")
    on_hand, reserved, available = position(db, product_code, store_number)
    return InventoryPositionResponse(
        product_code=product_code,
        store_number=store_number,
        on_hand=on_hand,
        reserved=reserved,
        available=available,
    )


@router.post(
    "/transfers", response_model=InventoryTransferResponse, status_code=status.HTTP_201_CREATED
)
def create_transfer(
    payload: InventoryTransferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.manage")),
) -> InventoryTransferResponse:
    if user.home_store_number and payload.from_store_number != user.home_store_number:
        raise HTTPException(status_code=403, detail="Store access denied")
    try:
        return InventoryTransferResponse.model_validate(post_transfer(db, payload, user.email))
    except InventoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/reservations",
    response_model=InventoryReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def reserve_inventory(
    payload: InventoryReservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.manage")),
) -> InventoryReservationResponse:
    if user.home_store_number and payload.store_number != user.home_store_number:
        raise HTTPException(status_code=403, detail="Store access denied")
    try:
        return InventoryReservationResponse.model_validate(
            create_reservation(db, payload, user.email)
        )
    except InventoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reservations/{reservation_id}/release", response_model=InventoryReservationResponse)
def release_inventory_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("receiving.manage")),
) -> InventoryReservationResponse:
    try:
        reservation = release_reservation(db, reservation_id)
    except InventoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return InventoryReservationResponse.model_validate(reservation)
