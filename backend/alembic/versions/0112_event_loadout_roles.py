"""Add sub-event-scoped loadout roles to event memberships."""

import sqlalchemy as sa

from alembic import op

revision = "0112_event_loadout_roles"
down_revision = "0111_event_venue_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_memberships",
        sa.Column("loadout_role", sa.String(length=24), nullable=True),
    )
    op.create_index(
        "ix_event_memberships_loadout_role",
        "event_memberships",
        ["loadout_role"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_memberships_loadout_role", table_name="event_memberships")
    op.drop_column("event_memberships", "loadout_role")
