"""Add non-ordering event filler slides.

Revision ID: 0084_event_filler_slides
Revises: 0083_event_cancellation_audit
"""

import sqlalchemy as sa

from alembic import op

revision = "0084_event_filler_slides"
down_revision = "0083_event_cancellation_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("event_presentation_states", "ordering_closes_at")
    op.drop_column("event_product_slides", "ordering_window_seconds")
    op.add_column(
        "event_product_slides",
        sa.Column("slide_type", sa.String(length=24), nullable=False, server_default="product"),
    )
    op.add_column(
        "event_product_slides",
        sa.Column("filler_category", sa.String(length=24), nullable=True),
    )
    op.create_index(
        "ix_event_product_slides_slide_type",
        "event_product_slides",
        ["slide_type"],
    )
    for column in (
        "model_number",
        "vendor_code",
        "event_unit_cost",
        "delivery_window_start",
        "delivery_window_end",
    ):
        op.alter_column("event_product_slides", column, existing_nullable=False, nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM event_product_slides WHERE slide_type = 'filler'")
    for column in (
        "model_number",
        "vendor_code",
        "event_unit_cost",
        "delivery_window_start",
        "delivery_window_end",
    ):
        op.alter_column("event_product_slides", column, existing_nullable=True, nullable=False)
    op.drop_index("ix_event_product_slides_slide_type", table_name="event_product_slides")
    op.drop_column("event_product_slides", "filler_category")
    op.drop_column("event_product_slides", "slide_type")
    op.add_column(
        "event_product_slides",
        sa.Column("ordering_window_seconds", sa.Integer(), nullable=False, server_default="900"),
    )
    op.add_column(
        "event_presentation_states",
        sa.Column("ordering_closes_at", sa.DateTime(timezone=True), nullable=True),
    )
