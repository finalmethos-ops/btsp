from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryLedgerEntry, InventoryReservation, InventoryTransfer
from app.schemas.inventory import (
    InventoryLedgerEntryCreate,
    InventoryReservationCreate,
    InventoryTransferCreate,
)


class InventoryError(ValueError):
    pass


def position(db: Session, product_code: str, store_number: str) -> tuple[Decimal, Decimal, Decimal]:
    on_hand = db.scalar(
        select(func.coalesce(func.sum(InventoryLedgerEntry.quantity_delta), 0)).where(
            InventoryLedgerEntry.product_code == product_code,
            InventoryLedgerEntry.store_number == store_number,
        )
    ) or Decimal("0")
    reserved = db.scalar(
        select(func.coalesce(func.sum(InventoryReservation.quantity), 0)).where(
            InventoryReservation.product_code == product_code,
            InventoryReservation.store_number == store_number,
            InventoryReservation.status == "active",
        )
    ) or Decimal("0")
    return Decimal(on_hand), Decimal(reserved), Decimal(on_hand) - Decimal(reserved)


def post_entry(
    db: Session, payload: InventoryLedgerEntryCreate, actor: str
) -> InventoryLedgerEntry:
    entry = InventoryLedgerEntry(**payload.model_dump(), actor=actor)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def post_transfer(db: Session, payload: InventoryTransferCreate, actor: str) -> InventoryTransfer:
    if payload.from_store_number == payload.to_store_number:
        raise InventoryError("Transfer source and destination must differ")
    _, _, available = position(db, payload.product_code, payload.from_store_number)
    if available < payload.quantity:
        raise InventoryError("Transfer quantity exceeds available inventory")
    transfer = InventoryTransfer(id=str(uuid4()), **payload.model_dump(), created_by=actor)
    db.add_all(
        [
            transfer,
            InventoryLedgerEntry(
                product_code=payload.product_code,
                store_number=payload.from_store_number,
                quantity_delta=-payload.quantity,
                reason="transfer_out",
                reference_type="inventory_transfer",
                reference_id=transfer.id,
                actor=actor,
            ),
            InventoryLedgerEntry(
                product_code=payload.product_code,
                store_number=payload.to_store_number,
                quantity_delta=payload.quantity,
                reason="transfer_in",
                reference_type="inventory_transfer",
                reference_id=transfer.id,
                actor=actor,
            ),
        ]
    )
    db.commit()
    db.refresh(transfer)
    return transfer


def create_reservation(
    db: Session, payload: InventoryReservationCreate, actor: str
) -> InventoryReservation:
    _, _, available = position(db, payload.product_code, payload.store_number)
    if available < payload.quantity:
        raise InventoryError("Reservation quantity exceeds available inventory")
    reservation = InventoryReservation(**payload.model_dump(), created_by=actor)
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def release_reservation(db: Session, reservation_id: str) -> InventoryReservation | None:
    reservation = db.get(InventoryReservation, reservation_id)
    if reservation is None:
        return None
    if reservation.status != "active":
        raise InventoryError("Reservation has already been released")
    from datetime import UTC, datetime

    reservation.status = "released"
    reservation.released_at = datetime.now(UTC)
    db.commit()
    db.refresh(reservation)
    return reservation
