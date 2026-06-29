from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReceiptSequence(Base):
    __tablename__ = "receipt_sequences"
    __table_args__ = (UniqueConstraint("prefix", "sequence_year", name="uq_receipt_sequence_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(24))
    sequence_year: Mapped[int]
    next_value: Mapped[int] = mapped_column(default=1)


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"
    __table_args__ = (
        UniqueConstraint("store_number", "external_receipt_id", name="uq_receipt_store_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    receipt_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    asn_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_advance_ship_notices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    external_receipt_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    receipt_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="posted", index=True)
    packing_slip_number: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["PurchaseReceiptLine"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan", order_by="PurchaseReceiptLine.id"
    )
    variances: Mapped[list["ReceiptVariance"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan", order_by="ReceiptVariance.id"
    )


class PurchaseReceiptLine(Base):
    __tablename__ = "purchase_receipt_lines"
    __table_args__ = (
        UniqueConstraint("receipt_id", "purchase_order_line_id", name="uq_receipt_po_line"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_receipts.id", ondelete="CASCADE"), index=True
    )
    purchase_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), index=True
    )
    asn_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_advance_ship_notice_lines.id", ondelete="SET NULL"), nullable=True
    )
    product_code: Mapped[str] = mapped_column(String(64))
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(160), nullable=True)

    receipt: Mapped[PurchaseReceipt] = relationship(back_populates="lines")
    variances: Mapped[list["ReceiptVariance"]] = relationship(back_populates="receipt_line")


class ReceiptVariance(Base):
    __tablename__ = "receipt_variances"
    __table_args__ = (
        UniqueConstraint("receipt_line_id", "variance_type", name="uq_receipt_line_variance"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_receipts.id", ondelete="CASCADE"), index=True
    )
    receipt_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_receipt_lines.id", ondelete="CASCADE"), index=True
    )
    variance_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    actual_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    difference_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resolution_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    receipt: Mapped[PurchaseReceipt] = relationship(back_populates="variances")
    receipt_line: Mapped[PurchaseReceiptLine] = relationship(back_populates="variances")


class BackorderSequence(Base):
    __tablename__ = "backorder_sequences"
    __table_args__ = (
        UniqueConstraint("prefix", "sequence_year", name="uq_backorder_sequence_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(24))
    sequence_year: Mapped[int]
    next_value: Mapped[int] = mapped_column(default=1)


class PurchaseBackorder(Base):
    __tablename__ = "purchase_backorders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    backorder_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_variance_id: Mapped[str] = mapped_column(
        ForeignKey("receipt_variances.id", ondelete="RESTRICT"), unique=True, index=True
    )
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    purchase_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), index=True
    )
    store_number: Mapped[str] = mapped_column(
        ForeignKey("stores.store_number", ondelete="RESTRICT"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(64))
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    fulfilled_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    outstanding_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    substitute_product_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["PurchaseBackorderEvent"]] = relationship(
        back_populates="backorder",
        cascade="all, delete-orphan",
        order_by="PurchaseBackorderEvent.id",
    )


class PurchaseBackorderEvent(Base):
    __tablename__ = "purchase_backorder_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    backorder_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_backorders.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(32), index=True)
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    note: Mapped[str] = mapped_column(String(1000))
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    backorder: Mapped[PurchaseBackorder] = relationship(back_populates="events")


class VendorInvoice(Base):
    __tablename__ = "vendor_invoices"
    __table_args__ = (
        UniqueConstraint("vendor_code", "invoice_number", name="uq_vendor_invoice_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_number: Mapped[str] = mapped_column(String(160))
    vendor_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"), index=True
    )
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    invoice_sha256: Mapped[str] = mapped_column(String(64), index=True)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    freight_total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(String(32), index=True)
    received_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["VendorInvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="VendorInvoiceLine.id"
    )


class VendorInvoiceLine(Base):
    __tablename__ = "vendor_invoice_lines"
    __table_args__ = (
        UniqueConstraint("invoice_id", "line_number", name="uq_vendor_invoice_line_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_invoices.id", ondelete="CASCADE"), index=True
    )
    line_number: Mapped[int]
    purchase_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    extended_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))

    invoice: Mapped[VendorInvoice] = relationship(back_populates="lines")
    match: Mapped["InvoiceLineMatch"] = relationship(
        back_populates="invoice_line", cascade="all, delete-orphan", uselist=False
    )


class InvoiceLineMatch(Base):
    __tablename__ = "invoice_line_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_line_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_invoice_lines.id", ondelete="CASCADE"), unique=True, index=True
    )
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    invoiced_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    quantity_difference: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    ordered_unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    invoiced_unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    price_difference: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(String(32), index=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice_line: Mapped[VendorInvoiceLine] = relationship(back_populates="match")


class InvoiceReconciliation(Base):
    __tablename__ = "invoice_reconciliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_invoices.id", ondelete="RESTRICT"), unique=True, index=True
    )
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exceptions: Mapped[list["ReconciliationException"]] = relationship(
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        order_by="ReconciliationException.created_at",
    )
    events: Mapped[list["ReconciliationEvent"]] = relationship(
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        order_by="ReconciliationEvent.id",
    )


class ReconciliationException(Base):
    __tablename__ = "reconciliation_exceptions"
    __table_args__ = (
        UniqueConstraint(
            "reconciliation_id",
            "invoice_line_id",
            "exception_type",
            name="uq_reconciliation_line_exception",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reconciliation_id: Mapped[str] = mapped_column(
        ForeignKey("invoice_reconciliations.id", ondelete="CASCADE"), index=True
    )
    invoice_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_invoice_lines.id", ondelete="CASCADE"), nullable=True, index=True
    )
    exception_type: Mapped[str] = mapped_column(String(32), index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    difference_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reconciliation: Mapped[InvoiceReconciliation] = relationship(back_populates="exceptions")


class ReconciliationEvent(Base):
    __tablename__ = "reconciliation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[str] = mapped_column(
        ForeignKey("invoice_reconciliations.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(32), index=True)
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(String(1000))
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reconciliation: Mapped[InvoiceReconciliation] = relationship(back_populates="events")
