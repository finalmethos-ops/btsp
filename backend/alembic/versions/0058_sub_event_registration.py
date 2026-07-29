"""add sub-event registration scope

Revision ID: 0058_sub_event_registration
Revises: 0057_event_attendee_categories
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_sub_event_registration"
down_revision: str | None = "0057_event_attendee_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_memberships",
        sa.Column(
            "sub_event_scope_configured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "event_sub_event_registrations",
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
        sa.Column("assigned_by", sa.String(320), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "sub_event_id", "membership_id", name="uq_event_sub_event_registration"
        ),
    )
    op.create_index(
        "ix_event_sub_event_registrations_event_id",
        "event_sub_event_registrations",
        ["event_id"],
    )
    op.create_index(
        "ix_event_sub_event_registrations_sub_event_id",
        "event_sub_event_registrations",
        ["sub_event_id"],
    )
    op.create_index(
        "ix_event_sub_event_registrations_membership_id",
        "event_sub_event_registrations",
        ["membership_id"],
    )


def downgrade() -> None:
    op.drop_table("event_sub_event_registrations")
    op.drop_column("event_memberships", "sub_event_scope_configured")
