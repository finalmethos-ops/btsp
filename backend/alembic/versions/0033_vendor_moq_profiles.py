"""vendor MOQ profiles and directional combinations

Revision ID: 0033_vendor_moq
Revises: 0032_vendor_models
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033_vendor_moq"
down_revision: str | None = "0032_vendor_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_moq_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("threshold_type", sa.String(24), nullable=False),
        sa.Column("threshold_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["vendor_code"], ["catalog_vendors.vendor_code"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("vendor_code", "code", name="uq_vendor_moq_code"),
    )
    op.create_index("ix_vendor_moq_rules_vendor_code", "vendor_moq_rules", ["vendor_code"])
    op.create_table(
        "vendor_moq_combinations",
        sa.Column("source_rule_id", sa.Integer(), primary_key=True),
        sa.Column("target_rule_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(["source_rule_id"], ["vendor_moq_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_rule_id"], ["vendor_moq_rules.id"], ondelete="CASCADE"),
    )
    op.add_column("catalog_products", sa.Column("moq_rule_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_catalog_products_moq_rule",
        "catalog_products",
        "vendor_moq_rules",
        ["moq_rule_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_catalog_products_moq_rule_id", "catalog_products", ["moq_rule_id"])
    op.execute(
        """
        INSERT INTO vendor_moq_rules (
            vendor_code, code, name, threshold_type, threshold_value, is_active
        )
        SELECT vendor_code, 'STANDARD', 'Standard MOQ', 'unit_quantity', 1, true
        FROM catalog_vendors
        """
    )
    op.execute(
        """
        UPDATE catalog_products p SET moq_rule_id = r.id
        FROM vendor_moq_rules r
        WHERE r.vendor_code = p.vendor_code AND r.code = 'STANDARD'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_products_moq_rule_id", table_name="catalog_products")
    op.drop_constraint("fk_catalog_products_moq_rule", "catalog_products", type_="foreignkey")
    op.drop_column("catalog_products", "moq_rule_id")
    op.drop_table("vendor_moq_combinations")
    op.drop_index("ix_vendor_moq_rules_vendor_code", table_name="vendor_moq_rules")
    op.drop_table("vendor_moq_rules")
