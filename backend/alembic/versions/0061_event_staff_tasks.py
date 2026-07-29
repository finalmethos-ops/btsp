"""add event staff tasks

Revision ID: 0061_event_staff_tasks
Revises: 0060_event_announcements
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0061_event_staff_tasks"
down_revision: str | None = "0060_event_announcements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_staff_tasks",
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
            sa.ForeignKey("managed_sub_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_membership_id",
            sa.String(36),
            sa.ForeignKey("event_memberships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_event_staff_tasks_event_id", ["event_id"]),
        ("ix_event_staff_tasks_sub_event_id", ["sub_event_id"]),
        ("ix_event_staff_tasks_assigned_membership_id", ["assigned_membership_id"]),
        ("ix_event_staff_tasks_priority", ["priority"]),
        ("ix_event_staff_tasks_status", ["status"]),
    ):
        op.create_index(name, "event_staff_tasks", columns)


def downgrade() -> None:
    op.drop_table("event_staff_tasks")
