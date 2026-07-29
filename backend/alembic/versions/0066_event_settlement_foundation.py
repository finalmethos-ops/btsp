"""add event settlement foundation

Revision ID: 0066_event_settlement_foundation
Revises: 0065_store_loadout_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0066_event_settlement_foundation"
down_revision: str | None = "0065_store_loadout_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "event_settlement_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(320), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("event_id", name="uq_event_settlement_event"),
    )
    op.create_index("ix_event_settlement_events_event_id", "event_settlement_events", ["event_id"])
    op.create_index("ix_event_settlement_events_status", "event_settlement_events", ["status"])

    op.create_table(
        "event_settlement_exceptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "settlement_event_id",
            sa.String(36),
            sa.ForeignKey("event_settlement_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exception_type", sa.String(48), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("reference_type", sa.String(48), nullable=True),
        sa.Column("reference_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_by", sa.String(320), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )
    for name, columns in (
        ("ix_event_settlement_exceptions_settlement_event_id", ["settlement_event_id"]),
        ("ix_event_settlement_exceptions_event_id", ["event_id"]),
        ("ix_event_settlement_exceptions_exception_type", ["exception_type"]),
        ("ix_event_settlement_exceptions_severity", ["severity"]),
        ("ix_event_settlement_exceptions_status", ["status"]),
        ("ix_event_settlement_exceptions_reference_type", ["reference_type"]),
        ("ix_event_settlement_exceptions_reference_id", ["reference_id"]),
    ):
        op.create_index(name, "event_settlement_exceptions", columns)

    op.create_table(
        "event_settlement_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "settlement_event_id",
            sa.String(36),
            sa.ForeignKey("event_settlement_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_event_settlement_audit_log_event_id", ["event_id"]),
        ("ix_event_settlement_audit_log_settlement_event_id", ["settlement_event_id"]),
        ("ix_event_settlement_audit_log_action", ["action"]),
    ):
        op.create_index(name, "event_settlement_audit_log", columns)


def downgrade() -> None:
    op.drop_table("event_settlement_audit_log")
    op.drop_table("event_settlement_exceptions")
    op.drop_table("event_settlement_events")
