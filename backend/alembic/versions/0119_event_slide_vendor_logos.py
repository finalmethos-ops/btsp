"""Add optional vendor logos to event presentation slides."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0119_event_slide_vendor_logos"
down_revision: str | None = "0118_event_slide_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_product_slide_vendor_logos",
        sa.Column("slide_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=320), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["slide_id"], ["event_product_slides.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slide_id"),
    )


def downgrade() -> None:
    op.drop_table("event_product_slide_vendor_logos")
