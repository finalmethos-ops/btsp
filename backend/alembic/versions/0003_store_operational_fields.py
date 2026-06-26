"""store operational fields

Revision ID: 0003_store_operational_fields
Revises: 0002_identity_rbac
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_store_operational_fields"
down_revision = "0002_identity_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("buying_group_code", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("operating_company", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("state_code", sa.String(length=2), nullable=True))
    op.add_column("stores", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("is_ordering_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_stores_buying_group_code", "stores", ["buying_group_code"])


def downgrade() -> None:
    op.drop_index("ix_stores_buying_group_code", table_name="stores")
    op.drop_column("stores", "is_ordering_enabled")
    op.drop_column("stores", "timezone")
    op.drop_column("stores", "state_code")
    op.drop_column("stores", "operating_company")
    op.drop_column("stores", "buying_group_code")
