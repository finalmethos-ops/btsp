"""Align purchasing, receiving, and backorder metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0104_purchasing_alignment"
down_revision = "0103_invoice_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    required_timestamps = (
        ("purchase_backorder_events", "created_at"),
        ("purchase_backorders", "created_at"),
        ("purchase_backorders", "updated_at"),
        ("purchase_order_artifacts", "created_at"),
        ("purchase_order_attention", "created_at"),
        ("purchase_order_transmission_events", "created_at"),
        ("purchase_order_transmissions", "created_at"),
        ("purchase_order_transmissions", "updated_at"),
        ("purchase_orders", "created_at"),
        ("purchase_orders", "updated_at"),
        ("purchase_receipts", "created_at"),
        ("purchase_request_attachments", "created_at"),
        ("purchase_request_line_items", "created_at"),
        ("purchase_request_line_items", "updated_at"),
        ("purchase_requests", "created_at"),
        ("purchase_requests", "updated_at"),
        ("vendor_purchase_order_acknowledgements", "created_at"),
    )
    for table, column in required_timestamps:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            existing_server_default=sa.text("now()"),
        )

    for old_name, new_name in (
        ("ix_backorder_event_action", "ix_purchase_backorder_events_action"),
        ("ix_backorder_event_backorder", "ix_purchase_backorder_events_backorder_id"),
        ("ix_backorder_purchase_order_id", "ix_purchase_backorders_purchase_order_id"),
        ("ix_backorder_purchase_order_line_id", "ix_purchase_backorders_purchase_order_line_id"),
        ("ix_backorder_backorder_number", "ix_purchase_backorders_backorder_number"),
        ("ix_backorder_source_variance_id", "ix_purchase_backorders_source_variance_id"),
        ("ix_backorder_status", "ix_purchase_backorders_status"),
        ("ix_backorder_store_number", "ix_purchase_backorders_store_number"),
        ("ix_receipt_asn_id", "ix_purchase_receipts_asn_id"),
        ("ix_receipt_line_po_line", "ix_purchase_receipt_lines_purchase_order_line_id"),
        ("ix_receipt_line_receipt", "ix_purchase_receipt_lines_receipt_id"),
        ("ix_receipt_purchase_order_id", "ix_purchase_receipts_purchase_order_id"),
        ("ix_receipt_receipt_number", "ix_purchase_receipts_receipt_number"),
        ("ix_receipt_receipt_sha256", "ix_purchase_receipts_receipt_sha256"),
        ("ix_receipt_status", "ix_purchase_receipts_status"),
        ("ix_receipt_store_number", "ix_purchase_receipts_store_number"),
        (
            "ix_vendor_asn_line_purchase_order_line_id",
            "ix_vendor_advance_ship_notice_lines_purchase_order_line_id",
        ),
        ("ix_vendor_asn_purchase_order_id", "ix_vendor_advance_ship_notices_purchase_order_id"),
        ("ix_vendor_shipment_purchase_order_id", "ix_vendor_shipments_purchase_order_id"),
    ):
        op.execute(f"ALTER INDEX {old_name} RENAME TO {new_name}")

    for index_name in (
        "ix_purchase_backorders_backorder_number",
        "ix_purchase_backorders_source_variance_id",
        "ix_purchase_orders_po_number",
        "ix_purchase_order_transmissions_artifact_id",
        "ix_purchase_receipts_receipt_number",
    ):
        # These columns already have database-backed unique constraints.
        op.drop_index(index_name)


def downgrade() -> None:
    for index_name, table, columns in (
        ("ix_purchase_receipts_receipt_number", "purchase_receipts", ["receipt_number"]),
        (
            "ix_purchase_order_transmissions_artifact_id",
            "purchase_order_transmissions",
            ["artifact_id"],
        ),
        ("ix_purchase_orders_po_number", "purchase_orders", ["po_number"]),
        (
            "ix_purchase_backorders_source_variance_id",
            "purchase_backorders",
            ["source_variance_id"],
        ),
        ("ix_purchase_backorders_backorder_number", "purchase_backorders", ["backorder_number"]),
    ):
        op.create_index(index_name, table, columns)

    for new_name, old_name in (
        ("ix_vendor_shipments_purchase_order_id", "ix_vendor_shipment_purchase_order_id"),
        (
            "ix_vendor_advance_ship_notices_purchase_order_id",
            "ix_vendor_asn_purchase_order_id",
        ),
        (
            "ix_vendor_advance_ship_notice_lines_purchase_order_line_id",
            "ix_vendor_asn_line_purchase_order_line_id",
        ),
        ("ix_purchase_receipts_store_number", "ix_receipt_store_number"),
        ("ix_purchase_receipts_status", "ix_receipt_status"),
        ("ix_purchase_receipts_purchase_order_id", "ix_receipt_purchase_order_id"),
        ("ix_purchase_receipt_lines_receipt_id", "ix_receipt_line_receipt"),
        ("ix_purchase_receipt_lines_purchase_order_line_id", "ix_receipt_line_po_line"),
        ("ix_purchase_receipts_asn_id", "ix_receipt_asn_id"),
        ("ix_purchase_backorders_store_number", "ix_backorder_store_number"),
        ("ix_purchase_backorders_status", "ix_backorder_status"),
        ("ix_purchase_backorders_backorder_number", "ix_backorder_backorder_number"),
        ("ix_purchase_backorders_purchase_order_line_id", "ix_backorder_purchase_order_line_id"),
        ("ix_purchase_backorders_purchase_order_id", "ix_backorder_purchase_order_id"),
        ("ix_purchase_backorder_events_backorder_id", "ix_backorder_event_backorder"),
        ("ix_purchase_backorder_events_action", "ix_backorder_event_action"),
    ):
        op.execute(f"ALTER INDEX {new_name} RENAME TO {old_name}")

    for table, column in reversed(
        (
            ("vendor_purchase_order_acknowledgements", "created_at"),
            ("purchase_requests", "updated_at"),
            ("purchase_requests", "created_at"),
            ("purchase_request_line_items", "updated_at"),
            ("purchase_request_line_items", "created_at"),
            ("purchase_request_attachments", "created_at"),
            ("purchase_receipts", "created_at"),
            ("purchase_orders", "updated_at"),
            ("purchase_orders", "created_at"),
            ("purchase_order_transmissions", "updated_at"),
            ("purchase_order_transmissions", "created_at"),
            ("purchase_order_transmission_events", "created_at"),
            ("purchase_order_attention", "created_at"),
            ("purchase_order_artifacts", "created_at"),
            ("purchase_backorders", "updated_at"),
            ("purchase_backorders", "created_at"),
            ("purchase_backorder_events", "created_at"),
        )
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            existing_server_default=sa.text("now()"),
        )
