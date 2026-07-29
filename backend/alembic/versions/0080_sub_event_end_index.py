"""Index sub-event end times used by schedules and access windows.

Revision ID: 0080_sub_event_end_index
Revises: 0079_event_schema_integrity
"""

from alembic import op

revision = "0080_sub_event_end_index"
down_revision = "0079_event_schema_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_managed_sub_events_ends_at",
        "managed_sub_events",
        ["ends_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_managed_sub_events_ends_at", table_name="managed_sub_events")
