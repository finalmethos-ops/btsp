"""Add editable product category to event presentation slides."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0118_event_slide_category"
down_revision: str | None = "0117_vendor_scoped_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_product_slides",
        sa.Column("category", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE event_product_slides AS slide
        SET category = COALESCE(product.product_category_code, product.department)
        FROM catalog_products AS product
        WHERE slide.catalog_product_code = product.product_code
          AND slide.category IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("event_product_slides", "category")
