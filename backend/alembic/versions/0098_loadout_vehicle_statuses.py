"""Track departure status for each store loadout vehicle."""

import sqlalchemy as sa

from alembic import op

revision = "0098_loadout_vehicle_statuses"
down_revision = "0097_loadout_vehicles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_loadout_assignments",
        sa.Column("vehicle_statuses", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("store_loadout_assignments", "vehicle_statuses")
