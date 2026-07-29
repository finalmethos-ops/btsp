"""apply sole active vendor MOQ to all existing models

Revision ID: 0046_single_moq
Revises: 0045_store_standard
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0046_single_moq"
down_revision: str | None = "0045_store_standard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE catalog_products AS product
            SET moq_rule_id = sole_rule.id
            FROM (
                SELECT vendor_code, min(id) AS id
                FROM vendor_moq_rules
                WHERE is_active IS TRUE
                GROUP BY vendor_code
                HAVING count(*) = 1
            ) AS sole_rule
            WHERE product.vendor_code = sole_rule.vendor_code
              AND product.moq_rule_id IS DISTINCT FROM sole_rule.id
            """
        )
    )


def downgrade() -> None:
    # Automatic assignments are valid model configuration and are retained.
    pass
