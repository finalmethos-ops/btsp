"""workflow engine

Revision ID: 0006_workflow_engine
Revises: 0005_configuration_entries
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_workflow_engine"
down_revision = "0005_configuration_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("initial_state", sa.String(length=128), nullable=False),
        sa.Column("terminal_states", sa.JSON(), nullable=False),
        sa.Column("transitions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_workflow_definition_code_version"),
    )
    op.create_index("ix_workflow_definitions_code", "workflow_definitions", ["code"])

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_code", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("current_state", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("started_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_instances_workflow_code", "workflow_instances", ["workflow_code"])
    op.create_index("ix_workflow_instances_entity_type", "workflow_instances", ["entity_type"])
    op.create_index("ix_workflow_instances_entity_id", "workflow_instances", ["entity_id"])
    op.create_index("ix_workflow_instances_current_state", "workflow_instances", ["current_state"])
    op.create_index("ix_workflow_instances_status", "workflow_instances", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_instances_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_current_state", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_entity_id", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_entity_type", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_workflow_code", table_name="workflow_instances")
    op.drop_table("workflow_instances")
    op.drop_index("ix_workflow_definitions_code", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
