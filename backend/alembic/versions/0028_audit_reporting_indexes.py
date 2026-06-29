"""audit reporting indexes

Revision ID: 0028_audit_reporting
Revises: 0027_analytics_reports
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_audit_reporting"
down_revision: str | None = "0027_analytics_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_event_snapshots_created_at", "event_snapshots", ["created_at"])
    op.create_index(
        "ix_event_snapshots_actor_created_at",
        "event_snapshots",
        ["actor", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_snapshots_actor_created_at", table_name="event_snapshots")
    op.drop_index("ix_event_snapshots_created_at", table_name="event_snapshots")
