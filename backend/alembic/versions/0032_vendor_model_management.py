"""vendor model management and cost history

Revision ID: 0032_vendor_models
Revises: 0031_numeric_precision
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_vendor_models"
down_revision: str | None = "0031_numeric_precision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_product_cost_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("vendor_code", sa.String(length=64), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=320), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_code"],
            ["catalog_products.product_code"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_catalog_cost_history_product_code",
        "catalog_product_cost_history",
        ["product_code"],
    )
    op.create_index(
        "ix_catalog_cost_history_vendor_code",
        "catalog_product_cost_history",
        ["vendor_code"],
    )
    op.create_index(
        "ix_catalog_cost_history_effective_from",
        "catalog_product_cost_history",
        ["effective_from"],
    )
    op.create_index(
        "ix_catalog_cost_history_effective_to",
        "catalog_product_cost_history",
        ["effective_to"],
    )
    op.execute(
        """
        INSERT INTO catalog_product_cost_history (
            product_code, vendor_code, unit_price, currency,
            effective_from, effective_to, changed_by, source
        )
        SELECT product_code, vendor_code, unit_price, currency,
               created_at, NULL, 'system-migration', 'migration'
        FROM catalog_products
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_cost_history_effective_to",
        table_name="catalog_product_cost_history",
    )
    op.drop_index(
        "ix_catalog_cost_history_effective_from",
        table_name="catalog_product_cost_history",
    )
    op.drop_index(
        "ix_catalog_cost_history_vendor_code",
        table_name="catalog_product_cost_history",
    )
    op.drop_index(
        "ix_catalog_cost_history_product_code",
        table_name="catalog_product_cost_history",
    )
    op.drop_table("catalog_product_cost_history")
