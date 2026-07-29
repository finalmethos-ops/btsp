"""Add visit completion to saved Vendor Hall booths.

Revision ID: 0078_vendor_hall_booth_visits
Revises: 0077_vendor_hall_saved_booths
"""

import sqlalchemy as sa

from alembic import op

revision = "0078_vendor_hall_booth_visits"
down_revision = "0077_vendor_hall_saved_booths"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_hall_saved_booths",
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendor_hall_saved_booths", "visited_at")
