"""use model numbers as canonical model identifiers

Revision ID: 0048_model_identifiers
Revises: 0047_store_read
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0048_model_identifiers"
down_revision: str | None = "0047_store_read"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM catalog_products
                WHERE NULLIF(BTRIM(model_number), '') IS NOT NULL
                GROUP BY BTRIM(model_number)
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION 'Model numbers must be unique before identifier migration';
            END IF;
            IF EXISTS (
                SELECT 1
                FROM catalog_products source
                JOIN catalog_products target
                  ON target.product_code = BTRIM(source.model_number)
                 AND target.id <> source.id
                WHERE NULLIF(BTRIM(source.model_number), '') IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'A model number conflicts with an existing model identifier';
            END IF;
            IF EXISTS (
                SELECT 1 FROM catalog_products
                WHERE LENGTH(BTRIM(model_number)) > 64
            ) THEN
                RAISE EXCEPTION 'Model numbers may not exceed 64 characters';
            END IF;
        END $$;
        """
    )
    op.drop_constraint(
        "catalog_product_cost_history_product_code_fkey",
        "catalog_product_cost_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "catalog_product_cost_history_product_code_fkey",
        "catalog_product_cost_history",
        "catalog_products",
        ["product_code"],
        ["product_code"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
    op.drop_constraint(
        "purchase_request_line_items_product_code_fkey",
        "purchase_request_line_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "purchase_request_line_items_product_code_fkey",
        "purchase_request_line_items",
        "catalog_products",
        ["product_code"],
        ["product_code"],
        onupdate="CASCADE",
    )
    op.execute(
        """
        CREATE TEMPORARY TABLE model_identifier_changes ON COMMIT DROP AS
        SELECT product_code AS old_identifier, BTRIM(model_number) AS new_identifier
        FROM catalog_products
        WHERE NULLIF(BTRIM(model_number), '') IS NOT NULL
          AND product_code <> BTRIM(model_number)
        """
    )
    op.execute(
        """
        UPDATE catalog_products product
        SET product_code = changes.new_identifier,
            model_number = changes.new_identifier
        FROM model_identifier_changes changes
        WHERE product.product_code = changes.old_identifier
        """
    )
    for statement in (
        "UPDATE purchase_request_line_items r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
        "UPDATE purchase_order_lines r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
        "UPDATE purchase_receipt_lines r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
        "UPDATE purchase_backorders r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
        "UPDATE vendor_advance_ship_notice_lines r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
        "UPDATE vendor_invoice_lines r SET product_code = c.new_identifier "
        "FROM model_identifier_changes c WHERE r.product_code = c.old_identifier",
    ):
        op.execute(statement)
    op.create_unique_constraint(
        "uq_catalog_products_model_number", "catalog_products", ["model_number"]
    )


def downgrade() -> None:
    # Canonical identifiers cannot be reconstructed after old synthetic codes are replaced.
    op.drop_constraint("uq_catalog_products_model_number", "catalog_products", type_="unique")
    op.drop_constraint(
        "catalog_product_cost_history_product_code_fkey",
        "catalog_product_cost_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "catalog_product_cost_history_product_code_fkey",
        "catalog_product_cost_history",
        "catalog_products",
        ["product_code"],
        ["product_code"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "purchase_request_line_items_product_code_fkey",
        "purchase_request_line_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "purchase_request_line_items_product_code_fkey",
        "purchase_request_line_items",
        "catalog_products",
        ["product_code"],
        ["product_code"],
    )
