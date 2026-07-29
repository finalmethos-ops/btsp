"""add event presentation state

Revision ID: 0052_event_presentation_state
Revises: 0051_event_slide_standard_cost
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0052_event_presentation_state"
down_revision: str | None = "0051_event_slide_standard_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_presentation_states",
        sa.Column(
            "sub_event_id",
            sa.String(36),
            sa.ForeignKey("managed_sub_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "current_slide_id",
            sa.String(36),
            sa.ForeignKey("event_product_slides.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("ordering_status", sa.String(24), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_event_presentation_states_event_id",
        "event_presentation_states",
        ["event_id"],
    )
    op.create_index(
        "ix_event_presentation_states_status",
        "event_presentation_states",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("event_presentation_states")
