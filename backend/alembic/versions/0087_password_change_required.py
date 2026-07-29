"""Require password rotation for provisioned accounts.

Revision ID: 0087_password_change_required
Revises: 0086_user_entity_scope
"""

import sqlalchemy as sa

from alembic import op

revision = "0087_password_change_required"
down_revision = "0086_user_entity_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_change_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_change_required")
