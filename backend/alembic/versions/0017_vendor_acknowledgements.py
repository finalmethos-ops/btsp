"""vendor purchase order acknowledgements

Revision ID: 0017_vendor_acknowledgements
Revises: 0016_vendor_integrations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_vendor_acknowledgements"
down_revision: str | None = "0016_vendor_integrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_purchase_order_acknowledgements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inbound_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "endpoint_id",
            sa.String(36),
            sa.ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("acknowledgement_status", sa.String(32), nullable=False),
        sa.Column("vendor_reference", sa.String(160)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("expected_ship_date", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.String(1000)),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("inbound_event_id", name="uq_vendor_po_ack_inbound_event"),
    )
    for name, column in (
        ("inbound_event", "inbound_event_id"),
        ("endpoint", "endpoint_id"),
        ("order", "purchase_order_id"),
        ("vendor", "vendor_code"),
        ("status", "acknowledgement_status"),
    ):
        op.create_index(
            f"ix_vendor_po_ack_{name}",
            "vendor_purchase_order_acknowledgements",
            [column],
        )


def downgrade() -> None:
    op.drop_table("vendor_purchase_order_acknowledgements")
