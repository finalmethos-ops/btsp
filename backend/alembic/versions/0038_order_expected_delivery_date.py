"""move expected delivery date to order and PO headers

Revision ID: 0038_expected_date
Revises: 0037_numbering
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0038_expected_date"
down_revision: str | None = "0037_numbering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "purchase_requests",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )
    # Use the latest line date when legacy lines disagree, avoiding a promise
    # earlier than one of the order's originally requested dates.
    op.execute(
        """
        UPDATE purchase_requests AS request
        SET expected_delivery_date = dates.expected_delivery_date
        FROM (
            SELECT purchase_request_id, MAX(requested_delivery_date) AS expected_delivery_date
            FROM purchase_request_line_items
            GROUP BY purchase_request_id
        ) AS dates
        WHERE request.id = dates.purchase_request_id
        """
    )
    op.execute(
        """
        UPDATE purchase_orders AS po
        SET expected_delivery_date = dates.expected_delivery_date
        FROM (
            SELECT purchase_order_id, MAX(requested_delivery_date) AS expected_delivery_date
            FROM purchase_order_lines
            GROUP BY purchase_order_id
        ) AS dates
        WHERE po.id = dates.purchase_order_id
        """
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "expected_delivery_date")
    op.drop_column("purchase_requests", "expected_delivery_date")
