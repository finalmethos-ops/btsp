"""Add event feedback responses.

Revision ID: 0089_event_feedback
Revises: 0088_entity_region_directory
"""

import sqlalchemy as sa

from alembic import op

revision = "0089_event_feedback"
down_revision = "0088_entity_region_directory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_feedback_responses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_feedback_response_user"),
    )
    op.create_index(
        "ix_event_feedback_responses_event_id", "event_feedback_responses", ["event_id"]
    )
    op.create_index("ix_event_feedback_responses_user_id", "event_feedback_responses", ["user_id"])


def downgrade() -> None:
    op.drop_table("event_feedback_responses")
