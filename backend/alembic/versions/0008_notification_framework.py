"""notification framework

Revision ID: 0008_notification_framework
Revises: 0007_workflow_metadata
Create Date: 2026-06-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_notification_framework"
down_revision = "0007_workflow_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_code", sa.String(length=160), nullable=False),
        sa.Column("workflow_code", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("subject_template", sa.String(length=500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("recipient_strategy", sa.String(length=64), nullable=False),
        sa.Column("recipient_config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_notification_templates_template_code",
        "notification_templates",
        ["template_code"],
        unique=True,
    )
    op.create_index(
        "ix_notification_templates_workflow_code", "notification_templates", ["workflow_code"]
    )
    op.create_index(
        "ix_notification_templates_event_type", "notification_templates", ["event_type"]
    )
    op.create_index("ix_notification_templates_channel", "notification_templates", ["channel"])

    op.create_table(
        "notification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_code", sa.String(length=160), nullable=False),
        sa.Column("workflow_code", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=320), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient_strategy", sa.String(length=64), nullable=False),
        sa.Column("resolved_recipients", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in (
        "template_code",
        "workflow_code",
        "event_type",
        "entity_type",
        "entity_id",
        "channel",
        "status",
    ):
        op.create_index(f"ix_notification_events_{column}", "notification_events", [column])


def downgrade() -> None:
    for column in (
        "status",
        "channel",
        "entity_id",
        "entity_type",
        "event_type",
        "workflow_code",
        "template_code",
    ):
        op.drop_index(f"ix_notification_events_{column}", table_name="notification_events")
    op.drop_table("notification_events")
    op.drop_index("ix_notification_templates_channel", table_name="notification_templates")
    op.drop_index("ix_notification_templates_event_type", table_name="notification_templates")
    op.drop_index("ix_notification_templates_workflow_code", table_name="notification_templates")
    op.drop_index("ix_notification_templates_template_code", table_name="notification_templates")
    op.drop_table("notification_templates")
