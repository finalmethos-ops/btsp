from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.catalog import CatalogProduct


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_code: Mapped[str] = mapped_column(String(128), index=True)
    workflow_instance_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflow_instances.id"), nullable=True, unique=True
    )
    store_number: Mapped[str] = mapped_column(ForeignKey("stores.store_number"), index=True)
    vendor_code: Mapped[str] = mapped_column(ForeignKey("catalog_vendors.vendor_code"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    freight_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(default=1)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    cloned_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("purchase_requests.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(320), index=True)
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    line_items: Mapped[list["PurchaseRequestLineItem"]] = relationship(
        back_populates="purchase_request",
        cascade="all, delete-orphan",
        order_by="PurchaseRequestLineItem.id",
    )


class PurchaseRequestLineItem(Base):
    __tablename__ = "purchase_request_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_request_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), index=True
    )
    product_code: Mapped[str] = mapped_column(ForeignKey("catalog_products.product_code"))
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    freight_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    extended_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    purchase_request: Mapped[PurchaseRequest] = relationship(back_populates="line_items")
    catalog_product: Mapped["CatalogProduct"] = relationship()
