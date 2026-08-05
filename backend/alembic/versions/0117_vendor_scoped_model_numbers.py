"""Allow different vendors to use the same model number."""

from collections.abc import Sequence

from alembic import op

revision: str = "0117_vendor_scoped_models"
down_revision: str | None = "0116_notification_action_href"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_catalog_products_model_number", "catalog_products", type_="unique")
    op.create_unique_constraint(
        "uq_catalog_products_vendor_model_number",
        "catalog_products",
        ["vendor_code", "model_number"],
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM catalog_products
                WHERE model_number IS NOT NULL
                GROUP BY model_number
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot restore global uniqueness while cross-vendor duplicates exist';
            END IF;
        END $$;
        """
    )
    op.drop_constraint(
        "uq_catalog_products_vendor_model_number",
        "catalog_products",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_catalog_products_model_number",
        "catalog_products",
        ["model_number"],
    )
