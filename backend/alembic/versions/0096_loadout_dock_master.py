"""Add dock-master and completion tracking to store loadout."""

import sqlalchemy as sa

from alembic import op

revision = "0096_loadout_dock_master"
down_revision = "0095_store_phone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_loadout_events", sa.Column("dock_master_email", sa.String(length=320), nullable=True)
    )
    op.add_column(
        "store_loadout_events", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("store_loadout_events", "completed_at")
    op.drop_column("store_loadout_events", "dock_master_email")
