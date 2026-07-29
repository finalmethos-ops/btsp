"""add event attendance

Revision ID: 0056_event_attendance
Revises: 0055_event_polling
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0056_event_attendance"
down_revision: str | None = "0055_event_polling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_attendance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_event_id",
            sa.String(36),
            sa.ForeignKey("managed_sub_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "membership_id",
            sa.String(36),
            sa.ForeignKey("event_memberships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True)),
        sa.Column("checked_out_at", sa.DateTime(timezone=True)),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("sub_event_id", "membership_id", name="uq_event_attendance_member"),
    )
    for name, columns in (
        ("ix_event_attendance_event_id", ["event_id"]),
        ("ix_event_attendance_sub_event_id", ["sub_event_id"]),
        ("ix_event_attendance_membership_id", ["membership_id"]),
        ("ix_event_attendance_status", ["status"]),
    ):
        op.create_index(name, "event_attendance", columns)


def downgrade() -> None:
    op.drop_table("event_attendance")
