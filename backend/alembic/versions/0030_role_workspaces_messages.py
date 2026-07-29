"""role workspaces and internal messages

Revision ID: 0030_role_workspaces
Revises: 0029_store_directory
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_role_workspaces"
down_revision: str | None = "0029_store_directory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("vendor_code", sa.String(length=64), nullable=True))
    op.create_index("ix_users_vendor_code", "users", ["vendor_code"])
    op.create_table(
        "internal_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_email", sa.String(length=320), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["sender_email"], ["users.email"]),
        sa.ForeignKeyConstraint(["recipient_email"], ["users.email"]),
    )
    op.create_index(
        "ix_internal_messages_recipient_created",
        "internal_messages",
        ["recipient_email", "created_at"],
    )
    op.create_index(
        "ix_internal_messages_sender_created",
        "internal_messages",
        ["sender_email", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_internal_messages_sender_created", table_name="internal_messages")
    op.drop_index("ix_internal_messages_recipient_created", table_name="internal_messages")
    op.drop_table("internal_messages")
    op.drop_index("ix_users_vendor_code", table_name="users")
    op.drop_column("users", "vendor_code")
