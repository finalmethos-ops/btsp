"""store directory details

Revision ID: 0029_store_directory
Revises: 0028_audit_reporting
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_store_directory"
down_revision: str | None = "0028_audit_reporting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("entity_code", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("purchasing_program", sa.String(length=32), nullable=True))
    op.add_column(
        "stores", sa.Column("regional_manager_name", sa.String(length=255), nullable=True)
    )
    op.add_column("stores", sa.Column("owner_operator_name", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("general_manager_name", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("manager_email", sa.String(length=320), nullable=True))
    op.add_column("stores", sa.Column("address_line1", sa.String(length=500), nullable=True))
    op.add_column("stores", sa.Column("city", sa.String(length=128), nullable=True))
    op.add_column("stores", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.create_index("ix_stores_entity_code", "stores", ["entity_code"])
    op.create_index("ix_stores_purchasing_program", "stores", ["purchasing_program"])


def downgrade() -> None:
    op.drop_index("ix_stores_purchasing_program", table_name="stores")
    op.drop_index("ix_stores_entity_code", table_name="stores")
    op.drop_column("stores", "postal_code")
    op.drop_column("stores", "city")
    op.drop_column("stores", "address_line1")
    op.drop_column("stores", "manager_email")
    op.drop_column("stores", "general_manager_name")
    op.drop_column("stores", "owner_operator_name")
    op.drop_column("stores", "regional_manager_name")
    op.drop_column("stores", "purchasing_program")
    op.drop_column("stores", "entity_code")
