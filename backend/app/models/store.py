from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    region_code: Mapped[str] = mapped_column(String(64), index=True)
    operating_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    purchasing_program: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    regional_manager_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_operator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    general_manager_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_ordering_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_system: Mapped[str] = mapped_column(String(128), default="official_store_database")
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class EntityRegion(Base):
    __tablename__ = "entity_regions"

    entity_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    region_code: Mapped[str] = mapped_column(String(64), primary_key=True)
