"""active PO attention workflow

Revision ID: 0039_po_attention
Revises: 0038_expected_date
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039_po_attention"
down_revision: str | None = "0038_expected_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("purchase_order_lines", "source_line_id", nullable=True)
    op.create_table(
        "purchase_order_attention",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("initiated_by_side", sa.String(16), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("response_note", sa.String(1000), nullable=True),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("responded_by", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_purchase_order_attention_purchase_order_id",
        "purchase_order_attention",
        ["purchase_order_id"],
    )
    op.create_index(
        "ix_purchase_order_attention_initiated_by_side",
        "purchase_order_attention",
        ["initiated_by_side"],
    )
    op.create_index(
        "ix_purchase_order_attention_action_type",
        "purchase_order_attention",
        ["action_type"],
    )
    op.create_index(
        "ix_purchase_order_attention_status",
        "purchase_order_attention",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("purchase_order_attention")
    op.alter_column("purchase_order_lines", "source_line_id", nullable=False)
