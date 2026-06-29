"""backorder lifecycle

Revision ID: 0024_backorders
Revises: 0023_receipt_variances
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_backorders"
down_revision: str | None = "0023_receipt_variances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backorder_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("sequence_year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.UniqueConstraint("prefix", "sequence_year", name="uq_backorder_sequence_year"),
    )
    op.create_table(
        "purchase_backorders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("backorder_number", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "source_variance_id",
            sa.String(36),
            sa.ForeignKey("receipt_variances.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "purchase_order_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "store_number",
            sa.String(32),
            sa.ForeignKey("stores.store_number", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("original_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("fulfilled_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("outstanding_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expected_at", sa.DateTime(timezone=True)),
        sa.Column("substitute_product_code", sa.String(64)),
        sa.Column("resolution_note", sa.String(1000)),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in (
        "backorder_number",
        "source_variance_id",
        "purchase_order_id",
        "purchase_order_line_id",
        "store_number",
        "status",
    ):
        op.create_index(f"ix_backorder_{column}", "purchase_backorders", [column])
    op.create_table(
        "purchase_backorder_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "backorder_id",
            sa.String(36),
            sa.ForeignKey("purchase_backorders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4)),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_backorder_event_backorder", "purchase_backorder_events", ["backorder_id"])
    op.create_index("ix_backorder_event_action", "purchase_backorder_events", ["action"])


def downgrade() -> None:
    op.drop_table("purchase_backorder_events")
    op.drop_table("purchase_backorders")
    op.drop_table("backorder_sequences")
