"""add event announcements

Revision ID: 0060_event_announcements
Revises: 0059_event_show_calendar
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0060_event_announcements"
down_revision: str | None = "0059_event_show_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_announcements",
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
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("visibility_categories", sa.JSON(), nullable=False),
        sa.Column("publishes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_event_announcements_event_id", ["event_id"]),
        ("ix_event_announcements_sub_event_id", ["sub_event_id"]),
        ("ix_event_announcements_severity", ["severity"]),
        ("ix_event_announcements_publishes_at", ["publishes_at"]),
        ("ix_event_announcements_is_active", ["is_active"]),
    ):
        op.create_index(name, "event_announcements", columns)


def downgrade() -> None:
    op.drop_table("event_announcements")
