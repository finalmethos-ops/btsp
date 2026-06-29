"""purchase order transmission lifecycle

Revision ID: 0015_po_transmissions
Revises: 0014_po_artifacts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_po_transmissions"
down_revision: str | None = "0014_po_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_transmissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            sa.String(36),
            sa.ForeignKey("purchase_order_artifacts.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("destination", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.String(1000)),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("purchase_order_id", "artifact_id", "channel", "status"):
        op.create_index(
            f"ix_purchase_order_transmissions_{column}",
            "purchase_order_transmissions",
            [column],
        )
    op.create_table(
        "purchase_order_transmission_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "transmission_id",
            sa.String(36),
            sa.ForeignKey("purchase_order_transmissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(1000)),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_purchase_order_transmission_events_transmission_id",
        "purchase_order_transmission_events",
        ["transmission_id"],
    )
    op.create_index(
        "ix_purchase_order_transmission_events_event_type",
        "purchase_order_transmission_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_table("purchase_order_transmission_events")
    op.drop_table("purchase_order_transmissions")
