"""commercial order and monthly store PO numbering

Revision ID: 0037_numbering
Revises: 0036_po_lifecycle
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037_numbering"
down_revision: str | None = "0036_po_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("purchase_requests", sa.Column("order_number", sa.String(255), nullable=True))
    op.execute("UPDATE purchase_requests SET order_number = 'LEGACY-' || id")
    op.alter_column("purchase_requests", "order_number", nullable=False)
    op.create_index("ix_purchase_requests_order_number", "purchase_requests", ["order_number"])

    op.add_column(
        "purchase_order_sequences",
        sa.Column("sequence_month", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_constraint("uq_po_sequence_prefix_year", "purchase_order_sequences", type_="unique")
    op.create_unique_constraint(
        "uq_po_sequence_prefix_year_month",
        "purchase_order_sequences",
        ["prefix", "sequence_year", "sequence_month"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_po_sequence_prefix_year_month", "purchase_order_sequences", type_="unique"
    )
    op.create_unique_constraint(
        "uq_po_sequence_prefix_year",
        "purchase_order_sequences",
        ["prefix", "sequence_year"],
    )
    op.drop_column("purchase_order_sequences", "sequence_month")
    op.drop_index("ix_purchase_requests_order_number", table_name="purchase_requests")
    op.drop_column("purchase_requests", "order_number")
