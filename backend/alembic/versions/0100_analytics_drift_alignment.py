"""Align analytics indexes and required timestamps with the models."""

import sqlalchemy as sa

from alembic import op

revision = "0100_analytics_alignment"
down_revision = "0099_loadout_item_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "analytics_report_runs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "analytics_report_schedules",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "analytics_report_schedules",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.execute(
        "ALTER INDEX ix_analytics_run_schedule RENAME TO ix_analytics_report_runs_schedule_id"
    )
    op.execute("ALTER INDEX ix_analytics_run_status RENAME TO ix_analytics_report_runs_status")
    op.execute(
        "ALTER INDEX ix_analytics_schedule_enabled RENAME TO "
        "ix_analytics_report_schedules_is_enabled"
    )
    op.execute(
        "ALTER INDEX ix_analytics_schedule_next RENAME TO ix_analytics_report_schedules_next_run_at"
    )
    op.execute(
        "ALTER INDEX ix_analytics_schedule_type RENAME TO ix_analytics_report_schedules_report_type"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_analytics_report_schedules_report_type RENAME TO ix_analytics_schedule_type"
    )
    op.execute(
        "ALTER INDEX ix_analytics_report_schedules_next_run_at RENAME TO ix_analytics_schedule_next"
    )
    op.execute(
        "ALTER INDEX ix_analytics_report_schedules_is_enabled RENAME TO "
        "ix_analytics_schedule_enabled"
    )
    op.execute("ALTER INDEX ix_analytics_report_runs_status RENAME TO ix_analytics_run_status")
    op.execute(
        "ALTER INDEX ix_analytics_report_runs_schedule_id RENAME TO ix_analytics_run_schedule"
    )
    op.alter_column("analytics_report_schedules", "updated_at", nullable=True)
    op.alter_column("analytics_report_schedules", "created_at", nullable=True)
    op.alter_column("analytics_report_runs", "created_at", nullable=True)
