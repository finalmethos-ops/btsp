"""Align receipt variance timestamps and index names."""

import sqlalchemy as sa

from alembic import op

revision = "0107_receipt_variances"
down_revision = "0106_identity_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill legacy rows before enforcing the model's required timestamp.
    op.execute("UPDATE receipt_variances SET detected_at = now() WHERE detected_at IS NULL")
    op.alter_column(
        "receipt_variances",
        "detected_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    for old_name, new_name in (
        ("ix_variance_receipt", "ix_receipt_variances_receipt_id"),
        ("ix_variance_receipt_line", "ix_receipt_variances_receipt_line_id"),
        ("ix_variance_severity", "ix_receipt_variances_severity"),
        ("ix_variance_status", "ix_receipt_variances_status"),
        ("ix_variance_type", "ix_receipt_variances_variance_type"),
    ):
        op.execute(f"ALTER INDEX {old_name} RENAME TO {new_name}")


def downgrade() -> None:
    for new_name, old_name in (
        ("ix_receipt_variances_variance_type", "ix_variance_type"),
        ("ix_receipt_variances_status", "ix_variance_status"),
        ("ix_receipt_variances_severity", "ix_variance_severity"),
        ("ix_receipt_variances_receipt_line_id", "ix_variance_receipt_line"),
        ("ix_receipt_variances_receipt_id", "ix_variance_receipt"),
    ):
        op.execute(f"ALTER INDEX {new_name} RENAME TO {old_name}")
    op.alter_column(
        "receipt_variances",
        "detected_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
