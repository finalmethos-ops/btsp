"""purchase order domain

Revision ID: 0012_purchase_orders
Revises: 0011_purchase_attachments
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_purchase_orders"
down_revision: str | None = "0011_purchase_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("sequence_year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.UniqueConstraint("prefix", "sequence_year", name="uq_po_sequence_prefix_year"),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("po_number", sa.String(64), nullable=False, unique=True),
        sa.Column("workflow_code", sa.String(128), nullable=False),
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
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("po_number", "workflow_code", "vendor_code", "status", "created_by"):
        op.create_index(f"ix_purchase_orders_{column}", "purchase_orders", [column])
    op.create_table(
        "purchase_order_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "purchase_request_id",
            sa.String(36),
            sa.ForeignKey("purchase_requests.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("store_number", sa.String(32), nullable=False),
    )
    for column in ("purchase_order_id", "purchase_request_id", "store_number"):
        op.create_index(f"ix_purchase_order_sources_{column}", "purchase_order_sources", [column])
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_request_id", sa.String(36), nullable=False),
        sa.Column(
            "source_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_request_line_items.id"),
            nullable=False,
        ),
        sa.Column("store_number", sa.String(32), nullable=False),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("freight_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("extended_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("notes", sa.String(1000)),
    )
    for column in ("purchase_order_id", "source_request_id", "store_number", "product_code"):
        op.create_index(f"ix_purchase_order_lines_{column}", "purchase_order_lines", [column])


def downgrade() -> None:
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_order_sources")
    op.drop_table("purchase_orders")
    op.drop_table("purchase_order_sequences")
