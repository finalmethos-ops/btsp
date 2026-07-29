"""Add event staff task phase.

Revision ID: 0090_event_staff_task_phase
Revises: 0089_event_feedback
"""

import sqlalchemy as sa

from alembic import op

revision = "0090_event_staff_task_phase"
down_revision = "0089_event_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_staff_tasks",
        sa.Column("task_phase", sa.String(length=24), nullable=False, server_default="live_event"),
    )
    op.create_index("ix_event_staff_tasks_task_phase", "event_staff_tasks", ["task_phase"])


def downgrade() -> None:
    op.drop_index("ix_event_staff_tasks_task_phase", table_name="event_staff_tasks")
    op.drop_column("event_staff_tasks", "task_phase")
