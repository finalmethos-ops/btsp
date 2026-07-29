"""Add notification action destinations."""

import sqlalchemy as sa

from alembic import op

revision = "0116_notification_action_href"
down_revision = "0115_staff_task_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_events",
        sa.Column("action_href", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_events", "action_href")
