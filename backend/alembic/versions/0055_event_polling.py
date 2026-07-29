"""add event polling

Revision ID: 0055_event_polling
Revises: 0054_event_order_review
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0055_event_polling"
down_revision: str | None = "0054_event_order_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_polls",
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
            nullable=False,
        ),
        sa.Column(
            "slide_id",
            sa.String(36),
            sa.ForeignKey("event_product_slides.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("show_results", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    for name, columns in (
        ("ix_event_polls_event_id", ["event_id"]),
        ("ix_event_polls_sub_event_id", ["sub_event_id"]),
        ("ix_event_polls_slide_id", ["slide_id"]),
        ("ix_event_polls_status", ["status"]),
    ):
        op.create_index(name, "event_polls", columns)
    op.create_table(
        "event_poll_options",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "poll_id",
            sa.String(36),
            sa.ForeignKey("event_polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.UniqueConstraint("poll_id", "position", name="uq_event_poll_option_position"),
    )
    op.create_index("ix_event_poll_options_poll_id", "event_poll_options", ["poll_id"])
    op.create_table(
        "event_poll_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poll_id",
            sa.String(36),
            sa.ForeignKey("event_polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "option_id",
            sa.String(36),
            sa.ForeignKey("event_poll_options.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("poll_id", "user_id", name="uq_event_poll_user_vote"),
    )
    op.create_index("ix_event_poll_votes_poll_id", "event_poll_votes", ["poll_id"])
    op.create_index("ix_event_poll_votes_option_id", "event_poll_votes", ["option_id"])
    op.create_index("ix_event_poll_votes_user_id", "event_poll_votes", ["user_id"])


def downgrade() -> None:
    op.drop_table("event_poll_votes")
    op.drop_table("event_poll_options")
    op.drop_table("event_polls")
