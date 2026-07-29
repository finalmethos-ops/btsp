"""Add vehicle manifests to store loadout assignments and items."""

import sqlalchemy as sa

from alembic import op

revision = "0097_loadout_vehicles"
down_revision = "0096_loadout_dock_master"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_loadout_assignments",
        sa.Column("vehicle_labels", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "store_loadout_items",
        sa.Column("vehicle_label", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("store_loadout_items", "vehicle_label")
    op.drop_column("store_loadout_assignments", "vehicle_labels")
