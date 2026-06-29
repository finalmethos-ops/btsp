from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class VendorEndpoint(Base):
    __tablename__ = "vendor_endpoints"
    __table_args__ = (
        UniqueConstraint("vendor_code", "name", name="uq_vendor_endpoint_vendor_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_code: Mapped[str] = mapped_column(ForeignKey("catalog_vendors.vendor_code"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    transport: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    external_vendor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connection_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["VendorInboundEvent"]] = relationship(back_populates="endpoint")
    import_runs: Mapped[list["VendorConnectorImportRun"]] = relationship(back_populates="endpoint")
    schedules: Mapped[list["VendorConnectorSchedule"]] = relationship(back_populates="endpoint")


class VendorConnectorSchedule(Base):
    __tablename__ = "vendor_connector_schedules"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "name", name="uq_vendor_schedule_endpoint_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    interval_minutes: Mapped[int]
    max_attempts: Mapped[int] = mapped_column(default=3)
    base_retry_seconds: Mapped[int] = mapped_column(default=60)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    endpoint: Mapped[VendorEndpoint] = relationship(back_populates="schedules")
    executions: Mapped[list["VendorConnectorExecution"]] = relationship(back_populates="schedule")


class VendorConnectorExecution(Base):
    __tablename__ = "vendor_connector_executions"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_for", name="uq_vendor_execution_schedule_time"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_connector_schedules.id", ondelete="RESTRICT"), index=True
    )
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"), index=True
    )
    import_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_connector_import_runs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempt_count: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int]
    base_retry_seconds: Mapped[int]
    worker_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lease_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    schedule: Mapped[VendorConnectorSchedule] = relationship(back_populates="executions")


class VendorConnectorImportRun(Base):
    __tablename__ = "vendor_connector_import_runs"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "content_sha256", name="uq_vendor_import_checksum"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"), index=True
    )
    source_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    event_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    imported_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    endpoint: Mapped[VendorEndpoint] = relationship(back_populates="import_runs")
    events: Mapped[list["VendorInboundEvent"]] = relationship(back_populates="import_run")


class VendorInboundEvent(Base):
    __tablename__ = "vendor_inbound_events"
    __table_args__ = (
        UniqueConstraint(
            "endpoint_id",
            "external_event_id",
            name="uq_vendor_inbound_event_endpoint_external",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"), index=True
    )
    import_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_connector_import_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    external_event_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    payload_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[str] = mapped_column(String(320))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    endpoint: Mapped[VendorEndpoint] = relationship(back_populates="events")
    import_run: Mapped[VendorConnectorImportRun | None] = relationship(back_populates="events")


class VendorPurchaseOrderAcknowledgement(Base):
    __tablename__ = "vendor_purchase_order_acknowledgements"
    __table_args__ = (
        UniqueConstraint("inbound_event_id", name="uq_vendor_po_ack_inbound_event"),
        Index("ix_vendor_po_ack_inbound_event", "inbound_event_id"),
        Index("ix_vendor_po_ack_endpoint", "endpoint_id"),
        Index("ix_vendor_po_ack_order", "purchase_order_id"),
        Index("ix_vendor_po_ack_vendor", "vendor_code"),
        Index("ix_vendor_po_ack_status", "acknowledgement_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inbound_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT")
    )
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"))
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT")
    )
    vendor_code: Mapped[str] = mapped_column(String(64))
    acknowledgement_status: Mapped[str] = mapped_column(String(32))
    vendor_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_ship_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorShipment(Base):
    __tablename__ = "vendor_shipments"
    __table_args__ = (
        UniqueConstraint("vendor_code", "shipment_number", name="uq_vendor_shipment_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    shipment_number: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), index=True)
    carrier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VendorShipmentUpdate(Base):
    __tablename__ = "vendor_shipment_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inbound_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT"), unique=True, index=True
    )
    shipment_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_shipments.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorAdvanceShipNotice(Base):
    __tablename__ = "vendor_advance_ship_notices"
    __table_args__ = (UniqueConstraint("vendor_code", "asn_number", name="uq_vendor_asn_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inbound_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT"), unique=True, index=True
    )
    purchase_order_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True
    )
    shipment_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_shipments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    asn_number: Mapped[str] = mapped_column(String(160))
    expected_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lines: Mapped[list["VendorAdvanceShipNoticeLine"]] = relationship(
        cascade="all, delete-orphan", order_by="VendorAdvanceShipNoticeLine.id"
    )


class VendorAdvanceShipNoticeLine(Base):
    __tablename__ = "vendor_advance_ship_notice_lines"
    __table_args__ = (
        UniqueConstraint("asn_id", "purchase_order_line_id", name="uq_vendor_asn_po_line"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asn_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_advance_ship_notices.id", ondelete="CASCADE"), index=True
    )
    purchase_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    lot_number: Mapped[str | None] = mapped_column(String(160), nullable=True)
