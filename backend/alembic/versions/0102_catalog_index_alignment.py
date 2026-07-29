"""Align catalog indexes and required product/vendor timestamps."""

import sqlalchemy as sa

from alembic import op

revision = "0102_catalog_index_alignment"
down_revision = "0101_catalog_import_timestamp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("catalog_products", "created_at"),
        ("catalog_products", "updated_at"),
        ("catalog_vendors", "created_at"),
        ("catalog_vendors", "updated_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            existing_server_default=sa.text("now()"),
        )

    for old_name, new_name in (
        (
            "ix_catalog_cost_history_effective_from",
            "ix_catalog_product_cost_history_effective_from",
        ),
        (
            "ix_catalog_cost_history_effective_to",
            "ix_catalog_product_cost_history_effective_to",
        ),
        (
            "ix_catalog_cost_history_product_code",
            "ix_catalog_product_cost_history_product_code",
        ),
        (
            "ix_catalog_cost_history_vendor_code",
            "ix_catalog_product_cost_history_vendor_code",
        ),
    ):
        op.execute(f"ALTER INDEX {old_name} RENAME TO {new_name}")

    for index_name in (
        "ix_catalog_products_model_number",
        "ix_catalog_products_product_code",
        "ix_catalog_vendors_vendor_code",
    ):
        op.drop_index(index_name)


def downgrade() -> None:
    op.create_index("ix_catalog_vendors_vendor_code", "catalog_vendors", ["vendor_code"])
    op.create_index("ix_catalog_products_product_code", "catalog_products", ["product_code"])
    op.create_index("ix_catalog_products_model_number", "catalog_products", ["model_number"])

    for new_name, old_name in (
        (
            "ix_catalog_product_cost_history_vendor_code",
            "ix_catalog_cost_history_vendor_code",
        ),
        (
            "ix_catalog_product_cost_history_product_code",
            "ix_catalog_cost_history_product_code",
        ),
        (
            "ix_catalog_product_cost_history_effective_to",
            "ix_catalog_cost_history_effective_to",
        ),
        (
            "ix_catalog_product_cost_history_effective_from",
            "ix_catalog_cost_history_effective_from",
        ),
    ):
        op.execute(f"ALTER INDEX {new_name} RENAME TO {old_name}")

    for table, column in (
        ("catalog_vendors", "updated_at"),
        ("catalog_vendors", "created_at"),
        ("catalog_products", "updated_at"),
        ("catalog_products", "created_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            existing_server_default=sa.text("now()"),
        )
