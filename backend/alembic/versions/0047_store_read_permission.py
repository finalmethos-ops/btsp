"""add read-only store directory permission

Revision ID: 0047_store_read
Revises: 0046_single_moq
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0047_store_read"
down_revision: str | None = "0046_single_moq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO permissions (code, description)
            VALUES ('stores.read', 'Read store authority records.')
            ON CONFLICT (code) DO UPDATE
            SET description = EXCLUDED.description
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT DISTINCT role.id, read_permission.id
            FROM roles AS role
            CROSS JOIN permissions AS read_permission
            LEFT JOIN role_permissions AS existing_management
              ON existing_management.role_id = role.id
            LEFT JOIN permissions AS management_permission
              ON management_permission.id = existing_management.permission_id
             AND management_permission.code = 'stores.manage'
            WHERE read_permission.code = 'stores.read'
              AND (role.code = 'RECONCILIATION' OR management_permission.id IS NOT NULL)
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id = "
            "(SELECT id FROM permissions WHERE code = 'stores.read')"
        )
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = 'stores.read'"))
