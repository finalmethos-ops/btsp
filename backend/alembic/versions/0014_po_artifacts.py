"""purchase order export artifacts

Revision ID: 0014_po_artifacts
Revises: 0013_po_splitting
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_po_artifacts"
down_revision: str | None = "0013_po_splitting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_format", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "purchase_order_id",
            "artifact_format",
            "version",
            name="uq_po_artifact_order_format_version",
        ),
    )
    for column in ("purchase_order_id", "artifact_format", "sha256"):
        op.create_index(
            f"ix_purchase_order_artifacts_{column}",
            "purchase_order_artifacts",
            [column],
        )


def downgrade() -> None:
    op.drop_table("purchase_order_artifacts")
