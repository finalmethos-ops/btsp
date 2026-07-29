"""Add staff task evidence attachments."""

import sqlalchemy as sa

from alembic import op

revision = "0115_staff_task_evidence"
down_revision = "0114_staff_task_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_staff_task_attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("event_staff_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_event_staff_task_attachments_task_id",
        "event_staff_task_attachments",
        ["task_id"],
    )
    op.create_index(
        "ix_event_staff_task_attachments_event_id",
        "event_staff_task_attachments",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_table("event_staff_task_attachments")
