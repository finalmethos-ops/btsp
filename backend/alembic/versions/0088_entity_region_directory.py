"""Add managed entity and region directory.

Revision ID: 0088_entity_region_directory
Revises: 0087_password_change_required
"""

import sqlalchemy as sa

from alembic import op

revision = "0088_entity_region_directory"
down_revision = "0087_password_change_required"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_regions",
        sa.Column("entity_code", sa.String(length=64), nullable=False),
        sa.Column("region_code", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("entity_code", "region_code"),
    )
    op.execute(
        """
        INSERT INTO entity_regions (entity_code, region_code)
        SELECT DISTINCT entity_code, region_code
        FROM stores
        WHERE entity_code IS NOT NULL AND region_code IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("entity_regions")
