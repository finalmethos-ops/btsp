"""Add entity scope to platform users.

Revision ID: 0086_user_entity_scope
Revises: 0085_multi_vendor_user_access
"""

import sqlalchemy as sa

from alembic import op

revision = "0086_user_entity_scope"
down_revision = "0085_multi_vendor_user_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("entity_code", sa.String(length=64), nullable=True))
    op.create_index("ix_users_entity_code", "users", ["entity_code"])


def downgrade() -> None:
    op.drop_index("ix_users_entity_code", table_name="users")
    op.drop_column("users", "entity_code")
