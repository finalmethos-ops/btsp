"""hash connector worker lease tokens

Revision ID: 0021_connector_security
Revises: 0020_connector_operations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_connector_security"
down_revision: str | None = "0020_connector_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "vendor_connector_executions",
        "lease_token",
        new_column_name="lease_token_hash",
    )
    executions = sa.table(
        "vendor_connector_executions",
        sa.column("status", sa.String()),
        sa.column("attempt_count", sa.Integer()),
        sa.column("max_attempts", sa.Integer()),
        sa.column("available_at", sa.DateTime(timezone=True)),
        sa.column("worker_id", sa.String()),
        sa.column("lease_token_hash", sa.String()),
        sa.column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.column("error_message", sa.String()),
        sa.column("completed_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        executions.update()
        .where(executions.c.status == "running")
        .values(
            status=sa.case(
                (executions.c.attempt_count >= executions.c.max_attempts, "dead_letter"),
                else_="retry",
            ),
            available_at=sa.func.now(),
            worker_id=None,
            lease_token_hash=None,
            lease_expires_at=None,
            error_message="Worker lease invalidated by connector security upgrade",
            completed_at=sa.case(
                (executions.c.attempt_count >= executions.c.max_attempts, sa.func.now()),
                else_=None,
            ),
        )
    )


def downgrade() -> None:
    op.alter_column(
        "vendor_connector_executions",
        "lease_token_hash",
        new_column_name="lease_token",
    )
