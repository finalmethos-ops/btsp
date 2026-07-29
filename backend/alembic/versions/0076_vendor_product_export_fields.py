"""Add vendor product export attributes.

Revision ID: 0076_vendor_product_fields
Revises: 0075_event_backup_artifacts
"""

import sqlalchemy as sa

from alembic import op

revision = "0076_vendor_product_fields"
down_revision = "0075_event_backup_artifacts"
branch_labels = None
depends_on = None

ELEMENTS_CATEGORY_PAIRS = (
    ("FURN BEDROOM", "FB-RAILS"),
    ("FURN BEDROOM", "HB-FB"),
    ("FURN DINING", "BAR"),
    ("FURN DINING", "DINING 8PC"),
    ("FURN LIVING ROOM", "MISC"),
    ("FURN LIVING ROOM", "SOFA-LOVE-CH"),
    ("FURN OUTDOOR", "CHAIR"),
    ("FURN OUTDOOR", "COCKTAIL"),
    ("FURN OUTDOOR", "LOVESEAT"),
    ("FURN OUTDOOR", "SEATING SET"),
    ("FURN OUTDOOR", "SECTIONAL"),
    ("FURN OUTDOOR", "SOFA"),
    ("FURN OUTDOOR", "SWING"),
    ("MISCELLANEOUS", "MISC"),
)


def upgrade() -> None:
    op.add_column(
        "catalog_products",
        sa.Column("is_clump", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "catalog_products",
        sa.Column("part_of_clump", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "catalog_products",
        sa.Column("cost_effective_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "catalog_products",
        sa.Column("cost_status", sa.String(length=32), nullable=False, server_default="Approved"),
    )
    op.create_index("ix_catalog_products_cost_status", "catalog_products", ["cost_status"])
    connection = op.get_bind()
    categories = sa.table(
        "model_categories",
        sa.column("department", sa.String()),
        sa.column("product_category_code", sa.String()),
        sa.column("status", sa.String()),
    )
    for department, product_code in ELEMENTS_CATEGORY_PAIRS:
        exists = connection.scalar(
            sa.select(sa.literal(1)).where(
                sa.exists(
                    sa.select(categories.c.department).where(
                        categories.c.department == department,
                        categories.c.product_category_code == product_code,
                    )
                )
            )
        )
        if not exists:
            connection.execute(
                categories.insert().values(
                    department=department,
                    product_category_code=product_code,
                    status="VALID",
                )
            )


def downgrade() -> None:
    op.drop_index("ix_catalog_products_cost_status", table_name="catalog_products")
    op.drop_column("catalog_products", "cost_status")
    op.drop_column("catalog_products", "cost_effective_start_date")
    op.drop_column("catalog_products", "part_of_clump")
    op.drop_column("catalog_products", "is_clump")
