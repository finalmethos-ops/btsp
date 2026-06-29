"""vendor shipments and advance ship notices

Revision ID: 0018_shipments_asns
Revises: 0017_vendor_acknowledgements
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_shipments_asns"
down_revision: str | None = "0017_vendor_acknowledgements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _indexes(table: str, prefix: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{prefix}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "vendor_shipments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("shipment_number", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("carrier", sa.String(160)),
        sa.Column("tracking_number", sa.String(160)),
        sa.Column("estimated_delivery_at", sa.DateTime(timezone=True)),
        sa.Column("shipped_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_code", "shipment_number", name="uq_vendor_shipment_number"),
    )
    _indexes(
        "vendor_shipments",
        "vendor_shipment",
        ("purchase_order_id", "vendor_code", "status", "tracking_number"),
    )
    op.create_table(
        "vendor_shipment_updates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inbound_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "shipment_id",
            sa.String(36),
            sa.ForeignKey("vendor_shipments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("location", sa.String(255)),
        sa.Column("notes", sa.String(1000)),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _indexes(
        "vendor_shipment_updates",
        "vendor_ship_update",
        ("inbound_event_id", "shipment_id", "status"),
    )
    op.create_table(
        "vendor_advance_ship_notices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inbound_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_inbound_events.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "shipment_id", sa.String(36), sa.ForeignKey("vendor_shipments.id", ondelete="SET NULL")
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("asn_number", sa.String(160), nullable=False),
        sa.Column("expected_delivery_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_code", "asn_number", name="uq_vendor_asn_number"),
    )
    _indexes(
        "vendor_advance_ship_notices",
        "vendor_asn",
        ("inbound_event_id", "purchase_order_id", "shipment_id", "vendor_code", "status"),
    )
    op.create_table(
        "vendor_advance_ship_notice_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asn_id",
            sa.String(36),
            sa.ForeignKey("vendor_advance_ship_notices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "purchase_order_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("lot_number", sa.String(160)),
        sa.UniqueConstraint("asn_id", "purchase_order_line_id", name="uq_vendor_asn_po_line"),
    )
    _indexes(
        "vendor_advance_ship_notice_lines", "vendor_asn_line", ("asn_id", "purchase_order_line_id")
    )


def downgrade() -> None:
    op.drop_table("vendor_advance_ship_notice_lines")
    op.drop_table("vendor_advance_ship_notices")
    op.drop_table("vendor_shipment_updates")
    op.drop_table("vendor_shipments")
