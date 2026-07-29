"""remove legacy free-text model category

Revision ID: 0042_remove_category
Revises: 0041_model_categories
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0042_remove_category"
down_revision: str | None = "0041_model_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_catalog_products_category", table_name="catalog_products")
    op.drop_column("catalog_products", "category")


def downgrade() -> None:
    op.add_column("catalog_products", sa.Column("category", sa.String(128), nullable=True))
    op.create_index("ix_catalog_products_category", "catalog_products", ["category"])
