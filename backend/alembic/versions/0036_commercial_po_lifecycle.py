"""vendor request through closed PO lifecycle

Revision ID: 0036_po_lifecycle
Revises: 0035_message_threads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_po_lifecycle"
down_revision: str | None = "0035_message_threads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("catalog_vendors", sa.Column("po_email_recipient", sa.String(320), nullable=True))
    op.add_column(
        "purchase_request_line_items",
        sa.Column("requested_delivery_date", sa.Date(), nullable=True),
    )
    op.add_column("purchase_orders", sa.Column("vendor_eta", sa.Date(), nullable=True))
    op.add_column(
        "purchase_orders",
        sa.Column("vendor_response_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders", sa.Column("vendor_rejection_reason", sa.String(1000), nullable=True)
    )
    op.add_column(
        "purchase_order_lines",
        sa.Column("received_quantity", sa.Numeric(14, 0), nullable=False, server_default="0"),
    )
    op.add_column(
        "purchase_order_lines", sa.Column("requested_delivery_date", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("purchase_order_lines", "requested_delivery_date")
    op.drop_column("purchase_order_lines", "received_quantity")
    op.drop_column("purchase_orders", "vendor_rejection_reason")
    op.drop_column("purchase_orders", "vendor_response_at")
    op.drop_column("purchase_orders", "vendor_eta")
    op.drop_column("purchase_request_line_items", "requested_delivery_date")
    op.drop_column("catalog_vendors", "po_email_recipient")
