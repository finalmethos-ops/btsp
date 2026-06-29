"""invoice reconciliation workflow

Revision ID: 0026_reconciliation
Revises: 0025_vendor_invoices
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_reconciliation"
down_revision: str | None = "0025_vendor_invoices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_reconciliations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.String(36),
            sa.ForeignKey("vendor_invoices.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("approved_by", sa.String(320)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_by", sa.String(320)),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_invoice", "invoice_reconciliations", ["invoice_id"])
    op.create_index("ix_reconciliation_order", "invoice_reconciliations", ["purchase_order_id"])
    op.create_index("ix_reconciliation_status", "invoice_reconciliations", ["status"])
    op.create_table(
        "reconciliation_exceptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "reconciliation_id",
            sa.String(36),
            sa.ForeignKey("invoice_reconciliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_line_id",
            sa.Integer(),
            sa.ForeignKey("vendor_invoice_lines.id", ondelete="CASCADE"),
        ),
        sa.Column("exception_type", sa.String(32), nullable=False),
        sa.Column("expected_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("actual_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("difference_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("disposition", sa.String(32)),
        sa.Column("resolution_note", sa.String(1000)),
        sa.Column("resolved_by", sa.String(320)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "reconciliation_id",
            "invoice_line_id",
            "exception_type",
            name="uq_reconciliation_line_exception",
        ),
    )
    for column in ("reconciliation_id", "invoice_line_id", "exception_type", "status"):
        op.create_index(f"ix_recon_exception_{column}", "reconciliation_exceptions", [column])
    op.create_table(
        "reconciliation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reconciliation_id",
            sa.String(36),
            sa.ForeignKey("invoice_reconciliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_event_case", "reconciliation_events", ["reconciliation_id"])
    op.create_index("ix_reconciliation_event_action", "reconciliation_events", ["action"])


def downgrade() -> None:
    op.drop_table("reconciliation_events")
    op.drop_table("reconciliation_exceptions")
    op.drop_table("invoice_reconciliations")
