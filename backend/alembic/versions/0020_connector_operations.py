"""connector schedules and operations

Revision ID: 0020_connector_operations
Revises: 0019_connector_imports
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_connector_operations"
down_revision: str | None = "0019_connector_imports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_connector_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "endpoint_id",
            sa.String(36),
            sa.ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("base_retry_seconds", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("endpoint_id", "name", name="uq_vendor_schedule_endpoint_name"),
    )
    op.create_index("ix_vendor_schedule_endpoint", "vendor_connector_schedules", ["endpoint_id"])
    op.create_index("ix_vendor_schedule_enabled", "vendor_connector_schedules", ["is_enabled"])
    op.create_index("ix_vendor_schedule_next_run", "vendor_connector_schedules", ["next_run_at"])
    op.create_table(
        "vendor_connector_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("vendor_connector_schedules.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "endpoint_id",
            sa.String(36),
            sa.ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "import_run_id",
            sa.String(36),
            sa.ForeignKey("vendor_connector_import_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("base_retry_seconds", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(160)),
        sa.Column("lease_token", sa.String(64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "schedule_id", "scheduled_for", name="uq_vendor_execution_schedule_time"
        ),
    )
    op.create_index("ix_vendor_execution_schedule", "vendor_connector_executions", ["schedule_id"])
    op.create_index("ix_vendor_execution_endpoint", "vendor_connector_executions", ["endpoint_id"])
    op.create_index("ix_vendor_execution_status", "vendor_connector_executions", ["status"])
    op.create_index(
        "ix_vendor_execution_available", "vendor_connector_executions", ["available_at"]
    )


def downgrade() -> None:
    op.drop_table("vendor_connector_executions")
    op.drop_table("vendor_connector_schedules")
