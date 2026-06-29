"""purchase request attachments

Revision ID: 0011_purchase_attachments
Revises: 0010_purchasing_drafts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_purchase_attachments"
down_revision: str | None = "0010_purchasing_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_request_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "purchase_request_id",
            sa.String(36),
            sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.String(320)),
    )
    for column in ("purchase_request_id", "category", "sha256", "is_deleted"):
        op.create_index(
            f"ix_purchase_request_attachments_{column}",
            "purchase_request_attachments",
            [column],
        )


def downgrade() -> None:
    op.drop_table("purchase_request_attachments")
