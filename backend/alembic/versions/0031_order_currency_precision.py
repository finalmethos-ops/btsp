"""enforce whole quantities and cent precision

Revision ID: 0031_numeric_precision
Revises: 0030_role_workspaces
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_numeric_precision"
down_revision: str | None = "0030_role_workspaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUANTITY_COLUMNS = {
    "catalog_products": ["minimum_order_quantity"],
    "purchase_request_line_items": ["quantity"],
    "purchase_order_lines": ["quantity"],
    "purchase_receipt_lines": [
        "received_quantity",
        "accepted_quantity",
        "rejected_quantity",
    ],
    "receipt_variances": [
        "expected_quantity",
        "actual_quantity",
        "difference_quantity",
    ],
    "purchase_backorders": [
        "original_quantity",
        "fulfilled_quantity",
        "outstanding_quantity",
    ],
    "purchase_backorder_events": ["quantity"],
    "vendor_invoice_lines": ["quantity"],
    "invoice_line_matches": [
        "ordered_quantity",
        "accepted_quantity",
        "invoiced_quantity",
        "quantity_difference",
    ],
    "vendor_advance_ship_notice_lines": ["quantity"],
}

MONEY_COLUMNS = {
    "catalog_products": ["unit_price"],
    "purchase_requests": ["subtotal", "freight_total", "tax_total", "total"],
    "purchase_request_line_items": [
        "unit_price",
        "freight_amount",
        "tax_amount",
        "extended_amount",
    ],
    "purchase_orders": ["subtotal", "freight_total", "tax_total", "total"],
    "purchase_order_lines": [
        "unit_price",
        "freight_amount",
        "tax_amount",
        "extended_amount",
    ],
    "vendor_invoices": ["subtotal", "freight_total", "tax_total", "total"],
    "vendor_invoice_lines": ["unit_price", "extended_amount"],
    "invoice_line_matches": [
        "ordered_unit_price",
        "invoiced_unit_price",
        "price_difference",
    ],
    "reconciliation_exceptions": [
        "expected_amount",
        "actual_amount",
        "difference_amount",
    ],
}


def _alter(columns: dict[str, list[str]], scale: int) -> None:
    target = sa.Numeric(14, scale)
    for table, names in columns.items():
        for column in names:
            op.alter_column(
                table,
                column,
                type_=target,
                existing_type=sa.Numeric(14, 4),
                postgresql_using=f"round({column}, {scale})",
            )


def upgrade() -> None:
    _alter(QUANTITY_COLUMNS, 0)
    _alter(MONEY_COLUMNS, 2)


def downgrade() -> None:
    for columns in (QUANTITY_COLUMNS, MONEY_COLUMNS):
        for table, names in columns.items():
            for column in names:
                op.alter_column(
                    table,
                    column,
                    type_=sa.Numeric(14, 4),
                    existing_type=sa.Numeric(14, 0 if columns is QUANTITY_COLUMNS else 2),
                    postgresql_using=f"{column}::numeric(14, 4)",
                )
