"""core purchasing domain and internal catalog

Revision ID: 0009_core_purchasing
Revises: 0008_notification_framework
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_core_purchasing"
down_revision: str | None = "0008_notification_framework"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_vendors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_code"),
    )
    op.create_index("ix_catalog_vendors_vendor_code", "catalog_vendors", ["vendor_code"])
    op.create_index("ix_catalog_vendors_is_active", "catalog_vendors", ["is_active"])
    op.create_table(
        "catalog_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model_number", sa.String(128)),
        sa.Column("category", sa.String(128)),
        sa.Column("brand", sa.String(128)),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("minimum_order_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_code"),
    )
    for column in (
        "product_code",
        "vendor_code",
        "model_number",
        "category",
        "brand",
        "is_available",
        "is_active",
    ):
        op.create_index(f"ix_catalog_products_{column}", "catalog_products", [column])
    op.create_table(
        "catalog_import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("vendor_rows", sa.Integer(), nullable=False),
        sa.Column("product_rows", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("imported_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_catalog_import_runs_status", "catalog_import_runs", ["status"])
    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_code", sa.String(128), nullable=False),
        sa.Column(
            "workflow_instance_id",
            sa.Integer(),
            sa.ForeignKey("workflow_instances.id"),
            unique=True,
        ),
        sa.Column(
            "store_number", sa.String(32), sa.ForeignKey("stores.store_number"), nullable=False
        ),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 4), nullable=False),
        sa.Column("freight_total", sa.Numeric(14, 4), nullable=False),
        sa.Column("tax_total", sa.Numeric(14, 4), nullable=False),
        sa.Column("total", sa.Numeric(14, 4), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("workflow_code", "store_number", "vendor_code", "status", "created_by"):
        op.create_index(f"ix_purchase_requests_{column}", "purchase_requests", [column])
    op.create_table(
        "purchase_request_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "purchase_request_id",
            sa.String(36),
            sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.String(64),
            sa.ForeignKey("catalog_products.product_code"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("freight_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("extended_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("notes", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_purchase_request_line_items_purchase_request_id",
        "purchase_request_line_items",
        ["purchase_request_id"],
    )


def downgrade() -> None:
    op.drop_table("purchase_request_line_items")
    op.drop_table("purchase_requests")
    op.drop_table("catalog_import_runs")
    op.drop_table("catalog_products")
    op.drop_table("catalog_vendors")
