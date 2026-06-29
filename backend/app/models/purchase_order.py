from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PurchaseOrderSequence(Base):
    __tablename__ = "purchase_order_sequences"
    __table_args__ = (
        UniqueConstraint("prefix", "sequence_year", name="uq_po_sequence_prefix_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(24))
    sequence_year: Mapped[int]
    next_value: Mapped[int] = mapped_column(default=1)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    po_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workflow_code: Mapped[str] = mapped_column(String(128), index=True)
    vendor_code: Mapped[str] = mapped_column(ForeignKey("catalog_vendors.vendor_code"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    freight_total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    created_by: Mapped[str] = mapped_column(String(320), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sources: Mapped[list["PurchaseOrderSource"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.id",
    )


class PurchaseOrderSource(Base):
    __tablename__ = "purchase_order_sources"
    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id",
            "purchase_request_id",
            name="uq_po_source_order_request",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    purchase_request_id: Mapped[str] = mapped_column(ForeignKey("purchase_requests.id"), index=True)
    store_number: Mapped[str] = mapped_column(String(32), index=True)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="sources")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    source_request_id: Mapped[str] = mapped_column(String(36), index=True)
    source_line_id: Mapped[int] = mapped_column(ForeignKey("purchase_request_line_items.id"))
    store_number: Mapped[str] = mapped_column(String(32), index=True)
    product_code: Mapped[str] = mapped_column(String(64), index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    freight_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    extended_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")


class PurchaseOrderArtifact(Base):
    __tablename__ = "purchase_order_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id",
            "artifact_format",
            "version",
            name="uq_po_artifact_order_format_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    artifact_format: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(default=1)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(160))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderTransmission(Base):
    __tablename__ = "purchase_order_transmissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_order_artifacts.id"), unique=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), index=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="prepared", index=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["PurchaseOrderTransmissionEvent"]] = relationship(
        back_populates="transmission",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderTransmissionEvent.id",
    )


class PurchaseOrderTransmissionEvent(Base):
    __tablename__ = "purchase_order_transmission_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    transmission_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_order_transmissions.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transmission: Mapped[PurchaseOrderTransmission] = relationship(back_populates="events")
