"""scheduled analytics reports

Revision ID: 0027_analytics_reports
Revises: 0026_reconciliation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_analytics_reports"
down_revision: str | None = "0026_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_report_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_analytics_report_schedule_name"),
    )
    op.create_index("ix_analytics_schedule_type", "analytics_report_schedules", ["report_type"])
    op.create_index("ix_analytics_schedule_next", "analytics_report_schedules", ["next_run_at"])
    op.create_index("ix_analytics_schedule_enabled", "analytics_report_schedules", ["is_enabled"])
    op.create_table(
        "analytics_report_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("analytics_report_schedules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stored_filename", sa.String(255), unique=True),
        sa.Column("content_type", sa.String(160)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("sha256", sa.String(64)),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("schedule_id", "scheduled_for", name="uq_analytics_run_schedule_time"),
    )
    op.create_index("ix_analytics_run_schedule", "analytics_report_runs", ["schedule_id"])
    op.create_index("ix_analytics_run_status", "analytics_report_runs", ["status"])


def downgrade() -> None:
    op.drop_table("analytics_report_runs")
    op.drop_table("analytics_report_schedules")
