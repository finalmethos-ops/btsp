"""Allow event vendor attendees to access selected vendor accounts."""

import sqlalchemy as sa

from alembic import op

revision = "0092_event_vendor_codes"
down_revision = "0091_user_notify_prefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_memberships",
        sa.Column("vendor_codes", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.execute(
        "UPDATE event_memberships SET vendor_codes = json_build_array(vendor_code) "
        "WHERE vendor_code IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("event_memberships", "vendor_codes")
