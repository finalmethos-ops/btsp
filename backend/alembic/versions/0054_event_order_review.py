"""add event order review and release staging

Revision ID: 0054_event_order_review
Revises: 0053_event_entity_ordering
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0054_event_order_review"
down_revision: str | None = "0053_event_entity_ordering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_entity_orders",
        sa.Column("review_status", sa.String(24), nullable=False, server_default="pending"),
    )
    op.add_column("event_entity_orders", sa.Column("reviewed_by", sa.String(320)))
    op.add_column("event_entity_orders", sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_event_entity_orders_review_status",
        "event_entity_orders",
        ["review_status"],
    )
    op.create_table(
        "event_order_review_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("event_entity_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(24), nullable=False),
        sa.Column("previous_quantity", sa.Integer(), nullable=False),
        sa.Column("resulting_quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_event_order_review_events_order_id", "event_order_review_events", ["order_id"]
    )
    op.create_index(
        "ix_event_order_review_events_decision", "event_order_review_events", ["decision"]
    )
    op.create_table(
        "event_order_release_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_event_order_release_batches_event_id",
        "event_order_release_batches",
        ["event_id"],
    )
    op.create_index(
        "ix_event_order_release_batches_status",
        "event_order_release_batches",
        ["status"],
    )
    op.create_table(
        "event_order_release_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("event_order_release_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("event_entity_orders.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("entity_code", sa.String(64), nullable=False),
        sa.Column("model_number", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(16, 2), nullable=False),
        sa.Column("requested_delivery_start", sa.Date(), nullable=False),
        sa.Column("requested_delivery_end", sa.Date(), nullable=False),
    )
    for name, columns in (
        ("ix_event_order_release_lines_batch_id", ["batch_id"]),
        ("ix_event_order_release_lines_order_id", ["order_id"]),
        ("ix_event_order_release_lines_vendor_code", ["vendor_code"]),
        ("ix_event_order_release_lines_entity_code", ["entity_code"]),
    ):
        op.create_index(name, "event_order_release_lines", columns)


def downgrade() -> None:
    op.drop_table("event_order_release_lines")
    op.drop_table("event_order_release_batches")
    op.drop_table("event_order_review_events")
    op.drop_index("ix_event_entity_orders_review_status", table_name="event_entity_orders")
    op.drop_column("event_entity_orders", "reviewed_at")
    op.drop_column("event_entity_orders", "reviewed_by")
    op.drop_column("event_entity_orders", "review_status")
