"""workflow definition metadata

Revision ID: 0007_workflow_metadata
Revises: 0006_workflow_engine
Create Date: 2026-06-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_workflow_metadata"
down_revision = "0006_workflow_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_definitions",
        sa.Column("business_area", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("category", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("configuration_namespace", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("states", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("workflow_definitions", "states")
    op.drop_column("workflow_definitions", "configuration_namespace")
    op.drop_column("workflow_definitions", "category")
    op.drop_column("workflow_definitions", "business_area")
