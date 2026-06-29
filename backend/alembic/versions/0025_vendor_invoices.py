"""vendor invoices and line matching

Revision ID: 0025_vendor_invoices
Revises: 0024_backorders
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_vendor_invoices"
down_revision: str | None = "0024_backorders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_number", sa.String(160), nullable=False),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("invoice_sha256", sa.String(64), nullable=False),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 4), nullable=False),
        sa.Column("freight_total", sa.Numeric(14, 4), nullable=False),
        sa.Column("tax_total", sa.Numeric(14, 4), nullable=False),
        sa.Column("total", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("received_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_code", "invoice_number", name="uq_vendor_invoice_number"),
    )
    for column in ("vendor_code", "purchase_order_id", "invoice_sha256", "status"):
        op.create_index(f"ix_invoice_{column}", "vendor_invoices", [column])
    op.create_table(
        "vendor_invoice_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.String(36),
            sa.ForeignKey("vendor_invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column(
            "purchase_order_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("extended_amount", sa.Numeric(14, 4), nullable=False),
        sa.UniqueConstraint("invoice_id", "line_number", name="uq_vendor_invoice_line_number"),
    )
    op.create_index("ix_invoice_line_invoice", "vendor_invoice_lines", ["invoice_id"])
    op.create_index("ix_invoice_line_po_line", "vendor_invoice_lines", ["purchase_order_line_id"])
    op.create_table(
        "invoice_line_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "invoice_line_id",
            sa.Integer(),
            sa.ForeignKey("vendor_invoice_lines.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ordered_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("invoiced_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("quantity_difference", sa.Numeric(14, 4), nullable=False),
        sa.Column("ordered_unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("invoiced_unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("price_difference", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoice_match_line", "invoice_line_matches", ["invoice_line_id"])
    op.create_index("ix_invoice_match_status", "invoice_line_matches", ["status"])


def downgrade() -> None:
    op.drop_table("invoice_line_matches")
    op.drop_table("vendor_invoice_lines")
    op.drop_table("vendor_invoices")
