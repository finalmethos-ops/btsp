"""model department and product category taxonomy

Revision ID: 0041_model_categories
Revises: 0040_invoice_intake
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_model_categories"
down_revision: str | None = "0040_invoice_intake"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department", sa.String(128), nullable=False),
        sa.Column("product_category_code", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.UniqueConstraint("department", "product_category_code", name="uq_model_category_pair"),
    )
    op.create_index("ix_model_categories_department", "model_categories", ["department"])
    op.create_index(
        "ix_model_categories_product_category_code",
        "model_categories",
        ["product_category_code"],
    )
    op.create_index("ix_model_categories_status", "model_categories", ["status"])
    op.add_column("catalog_products", sa.Column("department", sa.String(128), nullable=True))
    op.add_column(
        "catalog_products",
        sa.Column("product_category_code", sa.String(128), nullable=True),
    )
    op.create_index("ix_catalog_products_department", "catalog_products", ["department"])
    op.create_index(
        "ix_catalog_products_product_category_code",
        "catalog_products",
        ["product_category_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_products_product_category_code", table_name="catalog_products")
    op.drop_index("ix_catalog_products_department", table_name="catalog_products")
    op.drop_column("catalog_products", "product_category_code")
    op.drop_column("catalog_products", "department")
    op.drop_table("model_categories")
