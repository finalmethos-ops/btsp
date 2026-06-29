"""purchase order splitting source links

Revision ID: 0013_po_splitting
Revises: 0012_purchase_orders
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_po_splitting"
down_revision: str | None = "0012_purchase_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "purchase_order_sources_purchase_request_id_key",
        "purchase_order_sources",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_po_source_order_request",
        "purchase_order_sources",
        ["purchase_order_id", "purchase_request_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_po_source_order_request", "purchase_order_sources", type_="unique")
    op.create_unique_constraint(
        "purchase_order_sources_purchase_request_id_key",
        "purchase_order_sources",
        ["purchase_request_id"],
    )
