"""store audit fields

Revision ID: 0004_store_audit_fields
Revises: 0003_store_operational_fields
Create Date: 2026-06-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_store_audit_fields"
down_revision = "0003_store_operational_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "source_system",
            sa.String(length=128),
            nullable=False,
            server_default="official_store_database",
        ),
    )
    op.add_column(
        "stores", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "stores",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("stores", "updated_at")
    op.drop_column("stores", "created_at")
    op.drop_column("stores", "source_updated_at")
    op.drop_column("stores", "source_system")
