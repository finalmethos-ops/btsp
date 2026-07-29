"""add event entity ordering

Revision ID: 0053_event_entity_ordering
Revises: 0052_event_presentation_state
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0053_event_entity_ordering"
down_revision: str | None = "0052_event_presentation_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_memberships", sa.Column("entity_code", sa.String(64), nullable=True))
    op.create_index("ix_event_memberships_entity_code", "event_memberships", ["entity_code"])
    op.create_table(
        "event_entity_orders",
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
            sa.ForeignKey("event_product_slides.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "membership_id",
            sa.String(36),
            sa.ForeignKey("event_memberships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("entity_code", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("requested_delivery_start", sa.Date(), nullable=False),
        sa.Column("requested_delivery_end", sa.Date(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(16, 2), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "sub_event_id", "slide_id", "entity_code", name="uq_event_entity_order"
        ),
    )
    for name, columns in (
        ("ix_event_entity_orders_event_id", ["event_id"]),
        ("ix_event_entity_orders_sub_event_id", ["sub_event_id"]),
        ("ix_event_entity_orders_slide_id", ["slide_id"]),
        ("ix_event_entity_orders_entity_code", ["entity_code"]),
        ("ix_event_entity_orders_status", ["status"]),
    ):
        op.create_index(name, "event_entity_orders", columns)
    op.create_table(
        "event_entity_order_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("event_entity_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("requested_delivery_start", sa.Date(), nullable=False),
        sa.Column("requested_delivery_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("changed_by", sa.String(320), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_event_entity_order_revisions_order_id", "event_entity_order_revisions", ["order_id"]
    )


def downgrade() -> None:
    op.drop_table("event_entity_order_revisions")
    op.drop_table("event_entity_orders")
    op.drop_index("ix_event_memberships_entity_code", table_name="event_memberships")
    op.drop_column("event_memberships", "entity_code")
