"""add event show calendar

Revision ID: 0059_event_show_calendar
Revises: 0058_sub_event_registration
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0059_event_show_calendar"
down_revision: str | None = "0058_sub_event_registration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_calendar_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_event_id",
            sa.String(36),
            sa.ForeignKey("managed_sub_events.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(24), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("visibility_categories", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_event_calendar_entries_event_id", ["event_id"]),
        ("ix_event_calendar_entries_sub_event_id", ["sub_event_id"]),
        ("ix_event_calendar_entries_entry_type", ["entry_type"]),
        ("ix_event_calendar_entries_starts_at", ["starts_at"]),
        ("ix_event_calendar_entries_is_active", ["is_active"]),
    ):
        op.create_index(name, "event_calendar_entries", columns)


def downgrade() -> None:
    op.drop_table("event_calendar_entries")
