"""event ordering windows

Revision ID: 0072_event_order_windows
Revises: 0071_event_slide_variants
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0072_event_order_windows"
down_revision: str | None = "0071_event_slide_variants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_product_slides",
        sa.Column("ordering_window_seconds", sa.Integer(), nullable=False, server_default="900"),
    )
    op.add_column(
        "event_presentation_states",
        sa.Column("ordering_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_presentation_states",
        sa.Column("ordering_closes_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_presentation_states", "ordering_closes_at")
    op.drop_column("event_presentation_states", "ordering_opened_at")
    op.drop_column("event_product_slides", "ordering_window_seconds")
