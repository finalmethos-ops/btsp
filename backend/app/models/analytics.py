from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnalyticsReportSchedule(Base):
    __tablename__ = "analytics_report_schedules"
    __table_args__ = (UniqueConstraint("name", name="uq_analytics_report_schedule_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(128))
    report_type: Mapped[str] = mapped_column(String(32), index=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    interval_minutes: Mapped[int]
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["AnalyticsReportRun"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class AnalyticsReportRun(Base):
    __tablename__ = "analytics_report_runs"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_for", name="uq_analytics_run_schedule_time"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id: Mapped[str] = mapped_column(
        ForeignKey("analytics_report_schedules.id", ondelete="CASCADE"), index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    content_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    schedule: Mapped[AnalyticsReportSchedule] = relationship(back_populates="runs")
