from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InventoryLedgerEntry(Base):
    __tablename__ = "inventory_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_code: Mapped[str] = mapped_column(String(64), index=True)
    store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    reason: Mapped[str] = mapped_column(String(32), index=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_code: Mapped[str] = mapped_column(String(64), index=True)
    store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryTransfer(Base):
    __tablename__ = "inventory_transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_code: Mapped[str] = mapped_column(String(64), index=True)
    from_store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    to_store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    status: Mapped[str] = mapped_column(String(16), default="posted", index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
