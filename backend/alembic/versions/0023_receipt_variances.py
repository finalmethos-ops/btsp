"""receipt variance detection

Revision ID: 0023_receipt_variances
Revises: 0022_receiving_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_receipt_variances"
down_revision: str | None = "0022_receiving_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipt_variances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "receipt_id",
            sa.String(36),
            sa.ForeignKey("purchase_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "receipt_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_receipt_lines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variance_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("actual_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("difference_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(320)),
        sa.Column("resolution_action", sa.String(32)),
        sa.Column("resolution_note", sa.String(1000)),
        sa.UniqueConstraint("receipt_line_id", "variance_type", name="uq_receipt_line_variance"),
    )
    op.create_index("ix_variance_receipt", "receipt_variances", ["receipt_id"])
    op.create_index("ix_variance_receipt_line", "receipt_variances", ["receipt_line_id"])
    op.create_index("ix_variance_type", "receipt_variances", ["variance_type"])
    op.create_index("ix_variance_severity", "receipt_variances", ["severity"])
    op.create_index("ix_variance_status", "receipt_variances", ["status"])


def downgrade() -> None:
    op.drop_table("receipt_variances")
