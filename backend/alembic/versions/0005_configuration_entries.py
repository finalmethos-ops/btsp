"""configuration entries

Revision ID: 0005_configuration_entries
Revises: 0004_store_audit_fields
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_configuration_entries"
down_revision = "0004_store_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuration_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scope_type", "scope_key", "key", name="uq_configuration_scope_key"),
    )
    op.create_index("ix_configuration_entries_scope_type", "configuration_entries", ["scope_type"])
    op.create_index("ix_configuration_entries_scope_key", "configuration_entries", ["scope_key"])
    op.create_index("ix_configuration_entries_key", "configuration_entries", ["key"])


def downgrade() -> None:
    op.drop_index("ix_configuration_entries_key", table_name="configuration_entries")
    op.drop_index("ix_configuration_entries_scope_key", table_name="configuration_entries")
    op.drop_index("ix_configuration_entries_scope_type", table_name="configuration_entries")
    op.drop_table("configuration_entries")
