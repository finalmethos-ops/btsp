"""Add staff task completion and blocker details."""

import sqlalchemy as sa

from alembic import op

revision = "0114_staff_task_details"
down_revision = "0113_sub_event_membership_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_staff_tasks",
        sa.Column("status_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "event_staff_tasks",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_staff_tasks",
        sa.Column("completed_by", sa.String(length=320), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_staff_tasks", "completed_by")
    op.drop_column("event_staff_tasks", "completed_at")
    op.drop_column("event_staff_tasks", "status_note")
