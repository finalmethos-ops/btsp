"""Add configuration change history and approval records."""

import sqlalchemy as sa

from alembic import op

revision = "0110_config_change_workflow"
down_revision = "0109_inventory_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuration_changes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("proposed_value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decision_note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("scope_type", "scope_key", "key", "status"):
        op.create_index(f"ix_configuration_changes_{column}", "configuration_changes", [column])


def downgrade() -> None:
    op.drop_table("configuration_changes")
