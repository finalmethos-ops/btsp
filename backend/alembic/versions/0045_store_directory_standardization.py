"""standardize store directory fields and identifiers

Revision ID: 0045_store_standard
Revises: 0044_store_timezones
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045_store_standard"
down_revision: str | None = "0044_store_timezones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REFERENCE_COLUMNS = (
    ("purchase_backorders", "store_number"),
    ("purchase_order_lines", "store_number"),
    ("purchase_order_sources", "store_number"),
    ("purchase_receipts", "store_number"),
    ("purchase_requests", "store_number"),
    ("users", "home_store_number"),
    ("invoice_intake_documents", "detected_store_number"),
)


def _normalized(column: str) -> str:
    return (
        f"CASE {column} "
        "WHEN 'V135222628055' THEN '9901' "
        "WHEN 'V140858589810' THEN '9902' "
        f"ELSE lpad({column}, 4, '0') END"
    )


def upgrade() -> None:
    op.drop_constraint(
        "purchase_backorders_store_number_fkey",
        "purchase_backorders",
        type_="foreignkey",
    )
    op.drop_constraint(
        "purchase_receipts_store_number_fkey",
        "purchase_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "purchase_requests_store_number_fkey",
        "purchase_requests",
        type_="foreignkey",
    )

    connection = op.get_bind()
    for table, column in REFERENCE_COLUMNS:
        connection.execute(
            sa.text(
                f'UPDATE "{table}" SET "{column}" = {_normalized(column)} '
                f'WHERE "{column}" IS NOT NULL AND "{column}" !~ \'^[0-9]{{4}}$\''
            )
        )
    connection.execute(
        sa.text(
            f"UPDATE stores SET store_number = {_normalized('store_number')} "
            "WHERE store_number !~ '^[0-9]{4}$'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE purchase_orders SET po_number = regexp_replace("
            "po_number, '^PO-([0-9]{3})-', 'PO-0\\1-') "
            "WHERE po_number ~ '^PO-[0-9]{3}-'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE purchase_order_sequences SET prefix = regexp_replace("
            "prefix, '^PO-([0-9]{3})$', 'PO-0\\1') "
            "WHERE prefix ~ '^PO-[0-9]{3}$'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE purchase_requests SET order_number = regexp_replace("
            "order_number, '-([0-9]{3})-', '-0\\1-') "
            "WHERE order_number ~ '-[0-9]{3}-'"
        )
    )

    op.create_foreign_key(
        "purchase_backorders_store_number_fkey",
        "purchase_backorders",
        "stores",
        ["store_number"],
        ["store_number"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "purchase_receipts_store_number_fkey",
        "purchase_receipts",
        "stores",
        ["store_number"],
        ["store_number"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "purchase_requests_store_number_fkey",
        "purchase_requests",
        "stores",
        ["store_number"],
        ["store_number"],
    )
    op.create_check_constraint(
        "ck_stores_store_number_four_digits",
        "stores",
        "store_number ~ '^[0-9]{4}$'",
    )
    op.drop_index("ix_stores_buying_group_code", table_name="stores")
    op.drop_column("stores", "buying_group_code")


def downgrade() -> None:
    op.add_column("stores", sa.Column("buying_group_code", sa.String(length=64), nullable=True))
    op.create_index("ix_stores_buying_group_code", "stores", ["buying_group_code"])
    op.drop_constraint("ck_stores_store_number_four_digits", "stores", type_="check")
