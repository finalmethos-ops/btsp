"""Align invoice and reconciliation metadata without changing data semantics."""

import sqlalchemy as sa

from alembic import op

revision = "0103_invoice_reconciliation"
down_revision = "0102_catalog_index_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("internal_messages", "created_at"),
        ("invoice_intake_documents", "created_at"),
        ("invoice_line_matches", "matched_at"),
        ("invoice_reconciliations", "created_at"),
        ("invoice_reconciliations", "updated_at"),
        ("reconciliation_events", "created_at"),
        ("reconciliation_exceptions", "created_at"),
        ("vendor_invoices", "created_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            existing_server_default=sa.text("now()"),
        )

    for old_name, new_name in (
        ("ix_invoice_invoice_sha256", "ix_vendor_invoices_invoice_sha256"),
        ("ix_invoice_purchase_order_id", "ix_vendor_invoices_purchase_order_id"),
        ("ix_invoice_status", "ix_vendor_invoices_status"),
        ("ix_invoice_vendor_code", "ix_vendor_invoices_vendor_code"),
        ("ix_invoice_line_invoice", "ix_vendor_invoice_lines_invoice_id"),
        ("ix_invoice_line_po_line", "ix_vendor_invoice_lines_purchase_order_line_id"),
        ("ix_invoice_match_status", "ix_invoice_line_matches_status"),
        ("ix_reconciliation_order", "ix_invoice_reconciliations_purchase_order_id"),
        ("ix_reconciliation_status", "ix_invoice_reconciliations_status"),
        ("ix_reconciliation_event_action", "ix_reconciliation_events_action"),
        ("ix_reconciliation_event_case", "ix_reconciliation_events_reconciliation_id"),
        ("ix_recon_exception_exception_type", "ix_reconciliation_exceptions_exception_type"),
        ("ix_recon_exception_invoice_line_id", "ix_reconciliation_exceptions_invoice_line_id"),
        ("ix_recon_exception_reconciliation_id", "ix_reconciliation_exceptions_reconciliation_id"),
        ("ix_recon_exception_status", "ix_reconciliation_exceptions_status"),
    ):
        op.execute(f"ALTER INDEX {old_name} RENAME TO {new_name}")

    for index_name in (
        "ix_invoice_intake_documents_sha256",
        "ix_invoice_match_line",
        "ix_reconciliation_invoice",
    ):
        op.drop_index(index_name)


def downgrade() -> None:
    op.create_index("ix_reconciliation_invoice", "invoice_reconciliations", ["invoice_id"])
    op.create_index("ix_invoice_match_line", "invoice_line_matches", ["invoice_line_id"])
    op.create_index("ix_invoice_intake_documents_sha256", "invoice_intake_documents", ["sha256"])

    for new_name, old_name in (
        ("ix_reconciliation_exceptions_status", "ix_recon_exception_status"),
        (
            "ix_reconciliation_exceptions_reconciliation_id",
            "ix_recon_exception_reconciliation_id",
        ),
        ("ix_reconciliation_exceptions_invoice_line_id", "ix_recon_exception_invoice_line_id"),
        (
            "ix_reconciliation_exceptions_exception_type",
            "ix_recon_exception_exception_type",
        ),
        ("ix_reconciliation_events_reconciliation_id", "ix_reconciliation_event_case"),
        ("ix_reconciliation_events_action", "ix_reconciliation_event_action"),
        ("ix_invoice_reconciliations_status", "ix_reconciliation_status"),
        (
            "ix_invoice_reconciliations_purchase_order_id",
            "ix_reconciliation_order",
        ),
        ("ix_invoice_line_matches_status", "ix_invoice_match_status"),
        ("ix_vendor_invoice_lines_purchase_order_line_id", "ix_invoice_line_po_line"),
        ("ix_vendor_invoice_lines_invoice_id", "ix_invoice_line_invoice"),
        ("ix_vendor_invoices_vendor_code", "ix_invoice_vendor_code"),
        ("ix_vendor_invoices_status", "ix_invoice_status"),
        ("ix_vendor_invoices_purchase_order_id", "ix_invoice_purchase_order_id"),
        ("ix_vendor_invoices_invoice_sha256", "ix_invoice_invoice_sha256"),
    ):
        op.execute(f"ALTER INDEX {new_name} RENAME TO {old_name}")

    for table, column in (
        ("vendor_invoices", "created_at"),
        ("reconciliation_exceptions", "created_at"),
        ("reconciliation_events", "created_at"),
        ("invoice_reconciliations", "updated_at"),
        ("invoice_reconciliations", "created_at"),
        ("invoice_line_matches", "matched_at"),
        ("invoice_intake_documents", "created_at"),
        ("internal_messages", "created_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            existing_server_default=sa.text("now()"),
        )
