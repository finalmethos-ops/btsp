"""receiving foundation

Revision ID: 0022_receiving_foundation
Revises: 0021_connector_security
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_receiving_foundation"
down_revision: str | None = "0021_connector_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipt_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("sequence_year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.UniqueConstraint("prefix", "sequence_year", name="uq_receipt_sequence_year"),
    )
    op.create_table(
        "purchase_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_number", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "asn_id",
            sa.String(36),
            sa.ForeignKey("vendor_advance_ship_notices.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "store_number",
            sa.String(32),
            sa.ForeignKey("stores.store_number", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_receipt_id", sa.String(160)),
        sa.Column("receipt_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("packing_slip_number", sa.String(160)),
        sa.Column("notes", sa.String(1000)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "store_number", "external_receipt_id", name="uq_receipt_store_external"
        ),
    )
    for column in (
        "receipt_number",
        "purchase_order_id",
        "asn_id",
        "store_number",
        "receipt_sha256",
        "status",
    ):
        op.create_index(f"ix_receipt_{column}", "purchase_receipts", [column])
    op.create_table(
        "purchase_receipt_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "receipt_id",
            sa.String(36),
            sa.ForeignKey("purchase_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "purchase_order_line_id",
            sa.Integer(),
            sa.ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "asn_line_id",
            sa.Integer(),
            sa.ForeignKey("vendor_advance_ship_notice_lines.id", ondelete="SET NULL"),
        ),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("received_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("rejected_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("rejection_reason", sa.String(1000)),
        sa.Column("lot_number", sa.String(160)),
        sa.UniqueConstraint("receipt_id", "purchase_order_line_id", name="uq_receipt_po_line"),
    )
    op.create_index("ix_receipt_line_receipt", "purchase_receipt_lines", ["receipt_id"])
    op.create_index("ix_receipt_line_po_line", "purchase_receipt_lines", ["purchase_order_line_id"])


def downgrade() -> None:
    op.drop_table("purchase_receipt_lines")
    op.drop_table("purchase_receipts")
    op.drop_table("receipt_sequences")
