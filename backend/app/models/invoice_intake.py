from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InvoiceIntakeDocument(Base):
    __tablename__ = "invoice_intake_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    invoice_number: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    detected_vendor_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detected_store_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    detected_po_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    suggested_purchase_order_id: Mapped[str | None] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="unreconciled", index=True)
    uploaded_by: Mapped[str] = mapped_column(String(320), index=True)
    uploader_vendor_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
