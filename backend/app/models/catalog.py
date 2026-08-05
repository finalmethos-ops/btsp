from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CatalogVendor(Base):
    __tablename__ = "catalog_vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255))
    po_email_recipient: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list["CatalogProduct"]] = relationship(back_populates="vendor")
    moq_rules: Mapped[list["VendorMOQRule"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )


class ModelCategory(Base):
    __tablename__ = "model_categories"
    __table_args__ = (
        UniqueConstraint("department", "product_category_code", name="uq_model_category_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    department: Mapped[str] = mapped_column(String(128), index=True)
    product_category_code: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(16), default="VALID", index=True)


class VendorMOQRule(Base):
    __tablename__ = "vendor_moq_rules"
    __table_args__ = (UniqueConstraint("vendor_code", "code", name="uq_vendor_moq_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    threshold_type: Mapped[str] = mapped_column(String(24))
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    vendor: Mapped[CatalogVendor] = relationship(back_populates="moq_rules")


class VendorMOQCombination(Base):
    __tablename__ = "vendor_moq_combinations"

    source_rule_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_moq_rules.id", ondelete="CASCADE"), primary_key=True
    )
    target_rule_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_moq_rules.id", ondelete="CASCADE"), primary_key=True
    )


class VendorStateExclusion(Base):
    __tablename__ = "vendor_state_exclusions"

    vendor_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="CASCADE"), primary_key=True
    )
    state_code: Mapped[str] = mapped_column(String(2), primary_key=True)


class CatalogProduct(Base):
    __tablename__ = "catalog_products"
    __table_args__ = (
        UniqueConstraint(
            "vendor_code",
            "model_number",
            name="uq_catalog_products_vendor_model_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(String(64), unique=True)
    vendor_code: Mapped[str] = mapped_column(ForeignKey("catalog_vendors.vendor_code"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    product_category_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_clump: Mapped[bool] = mapped_column(Boolean, default=False)
    part_of_clump: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_effective_start_date: Mapped[date | None] = mapped_column(nullable=True)
    cost_status: Mapped[str] = mapped_column(String(32), default="Approved", index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    minimum_order_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 0), default=1)
    moq_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_moq_rules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendor: Mapped[CatalogVendor] = relationship(back_populates="products")
    cost_history: Mapped[list["CatalogProductCostHistory"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="CatalogProductCostHistory.effective_from.desc()",
    )


class CatalogProductCostHistory(Base):
    __tablename__ = "catalog_product_cost_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_products.product_code", ondelete="CASCADE", onupdate="CASCADE"),
        index=True,
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    changed_by: Mapped[str] = mapped_column(String(320))
    source: Mapped[str] = mapped_column(String(32))

    product: Mapped[CatalogProduct] = relationship(back_populates="cost_history")


class CatalogImportRun(Base):
    __tablename__ = "catalog_import_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    vendor_rows: Mapped[int] = mapped_column(default=0)
    product_rows: Mapped[int] = mapped_column(default=0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    imported_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
