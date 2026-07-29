"""add event vendor booths

Revision ID: 0062_event_vendor_booths
Revises: 0061_event_staff_tasks
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0062_event_vendor_booths"
down_revision: str | None = "0061_event_staff_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_vendor_booths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("booth_name", sa.String(255), nullable=False),
        sa.Column("booth_number", sa.String(64), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", "vendor_code", name="uq_event_vendor_booth"),
    )
    for name, columns in (
        ("ix_event_vendor_booths_event_id", ["event_id"]),
        ("ix_event_vendor_booths_vendor_code", ["vendor_code"]),
        ("ix_event_vendor_booths_status", ["status"]),
    ):
        op.create_index(name, "event_vendor_booths", columns)


def downgrade() -> None:
    op.drop_table("event_vendor_booths")
