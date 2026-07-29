"""Add attendee-saved Vendor Hall booths.

Revision ID: 0077_vendor_hall_saved_booths
Revises: 0076_vendor_product_fields
"""

import sqlalchemy as sa

from alembic import op

revision = "0077_vendor_hall_saved_booths"
down_revision = "0076_vendor_product_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_hall_saved_booths",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("membership_id", sa.String(length=36), nullable=False),
        sa.Column("vendor_hall_booth_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["managed_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["membership_id"], ["event_memberships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["vendor_hall_booth_id"], ["vendor_hall_booths.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id",
            "vendor_hall_booth_id",
            name="uq_vendor_hall_saved_booth_membership",
        ),
    )
    op.create_index(
        "ix_vendor_hall_saved_booths_event_id",
        "vendor_hall_saved_booths",
        ["event_id"],
    )
    op.create_index(
        "ix_vendor_hall_saved_booths_membership_id",
        "vendor_hall_saved_booths",
        ["membership_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_hall_saved_booths_membership_id",
        table_name="vendor_hall_saved_booths",
    )
    op.drop_index(
        "ix_vendor_hall_saved_booths_event_id",
        table_name="vendor_hall_saved_booths",
    )
    op.drop_table("vendor_hall_saved_booths")
