"""thread internal messages into conversations

Revision ID: 0035_message_threads
Revises: 0034_vendor_states
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_message_threads"
down_revision: str | None = "0034_vendor_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("internal_messages", sa.Column("conversation_id", sa.String(64), nullable=True))
    op.execute("UPDATE internal_messages SET conversation_id = 'legacy-' || id::text")
    op.alter_column("internal_messages", "conversation_id", nullable=False)
    op.create_index(
        "ix_internal_messages_conversation_id", "internal_messages", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_internal_messages_conversation_id", table_name="internal_messages")
    op.drop_column("internal_messages", "conversation_id")
