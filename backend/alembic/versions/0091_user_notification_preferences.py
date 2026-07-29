"""Add user notification preferences.

Revision ID: 0091_user_notification_preferences
Revises: 0090_event_staff_task_phase
"""

import sqlalchemy as sa

from alembic import op

revision = "0091_user_notify_prefs"
down_revision = "0090_event_staff_task_phase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notification_preferences",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("user_notification_preferences")
