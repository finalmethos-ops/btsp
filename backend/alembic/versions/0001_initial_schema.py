"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_number", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region_code", sa.String(length=64), nullable=False),
        sa.Column("district_code", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_stores_id", "stores", ["id"])
    op.create_index("ix_stores_store_number", "stores", ["store_number"], unique=True)
    op.create_index("ix_stores_region_code", "stores", ["region_code"])

    op.create_table(
        "event_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_event_snapshots_event_type", "event_snapshots", ["event_type"])
    op.create_index("ix_event_snapshots_entity_type", "event_snapshots", ["entity_type"])
    op.create_index("ix_event_snapshots_entity_id", "event_snapshots", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_event_snapshots_entity_id", table_name="event_snapshots")
    op.drop_index("ix_event_snapshots_entity_type", table_name="event_snapshots")
    op.drop_index("ix_event_snapshots_event_type", table_name="event_snapshots")
    op.drop_table("event_snapshots")
    op.drop_index("ix_stores_region_code", table_name="stores")
    op.drop_index("ix_stores_store_number", table_name="stores")
    op.drop_index("ix_stores_id", table_name="stores")
    op.drop_table("stores")
