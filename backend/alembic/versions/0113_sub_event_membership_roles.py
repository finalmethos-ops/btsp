"""Add per-sub-event attendee roles."""

import sqlalchemy as sa

from alembic import op

revision = "0113_sub_event_membership_roles"
down_revision = "0112_event_loadout_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_sub_event_registrations",
        sa.Column("role", sa.String(length=24), nullable=True),
    )
    op.create_index(
        "ix_event_sub_event_registrations_role",
        "event_sub_event_registrations",
        ["role"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_sub_event_registrations_role",
        table_name="event_sub_event_registrations",
    )
    op.drop_column("event_sub_event_registrations", "role")
