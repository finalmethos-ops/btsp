"""Align vendor connector, shipment, and ASN metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0105_vendor_integration"
down_revision = "0104_purchasing_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("vendor_advance_ship_notices", "created_at"),
        ("vendor_connector_executions", "created_at"),
        ("vendor_connector_import_runs", "created_at"),
        ("vendor_connector_schedules", "created_at"),
        ("vendor_connector_schedules", "updated_at"),
        ("vendor_endpoints", "created_at"),
        ("vendor_endpoints", "updated_at"),
        ("vendor_inbound_events", "received_at"),
        ("vendor_shipment_updates", "created_at"),
        ("vendor_shipments", "created_at"),
        ("vendor_shipments", "updated_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            existing_server_default=sa.text("now()"),
        )

    for old_name, new_name in (
        ("ix_vendor_asn_line_asn_id", "ix_vendor_advance_ship_notice_lines_asn_id"),
        ("ix_vendor_asn_inbound_event_id", "ix_vendor_advance_ship_notices_inbound_event_id"),
        ("ix_vendor_asn_shipment_id", "ix_vendor_advance_ship_notices_shipment_id"),
        ("ix_vendor_asn_status", "ix_vendor_advance_ship_notices_status"),
        ("ix_vendor_asn_vendor_code", "ix_vendor_advance_ship_notices_vendor_code"),
        ("ix_vendor_execution_available", "ix_vendor_connector_executions_available_at"),
        ("ix_vendor_execution_endpoint", "ix_vendor_connector_executions_endpoint_id"),
        ("ix_vendor_execution_schedule", "ix_vendor_connector_executions_schedule_id"),
        ("ix_vendor_execution_status", "ix_vendor_connector_executions_status"),
        ("ix_vendor_import_checksum", "ix_vendor_connector_import_runs_content_sha256"),
        ("ix_vendor_import_endpoint", "ix_vendor_connector_import_runs_endpoint_id"),
        ("ix_vendor_import_status", "ix_vendor_connector_import_runs_status"),
        ("ix_vendor_schedule_enabled", "ix_vendor_connector_schedules_is_enabled"),
        ("ix_vendor_schedule_endpoint", "ix_vendor_connector_schedules_endpoint_id"),
        ("ix_vendor_schedule_next_run", "ix_vendor_connector_schedules_next_run_at"),
        ("ix_vendor_event_import_run", "ix_vendor_inbound_events_import_run_id"),
        ("ix_vendor_ship_update_inbound_event_id", "ix_vendor_shipment_updates_inbound_event_id"),
        ("ix_vendor_ship_update_shipment_id", "ix_vendor_shipment_updates_shipment_id"),
        ("ix_vendor_ship_update_status", "ix_vendor_shipment_updates_status"),
        ("ix_vendor_shipment_status", "ix_vendor_shipments_status"),
        ("ix_vendor_shipment_tracking_number", "ix_vendor_shipments_tracking_number"),
        ("ix_vendor_shipment_vendor_code", "ix_vendor_shipments_vendor_code"),
    ):
        op.execute(f"ALTER INDEX {old_name} RENAME TO {new_name}")

    op.drop_index("ix_vendor_shipment_updates_inbound_event_id")
    op.drop_index("ix_vendor_advance_ship_notices_inbound_event_id")


def downgrade() -> None:
    op.create_index(
        "ix_vendor_advance_ship_notices_inbound_event_id",
        "vendor_advance_ship_notices",
        ["inbound_event_id"],
    )
    op.create_index(
        "ix_vendor_shipment_updates_inbound_event_id",
        "vendor_shipment_updates",
        ["inbound_event_id"],
    )

    for new_name, old_name in (
        ("ix_vendor_shipments_vendor_code", "ix_vendor_shipment_vendor_code"),
        ("ix_vendor_shipments_tracking_number", "ix_vendor_shipment_tracking_number"),
        ("ix_vendor_shipments_status", "ix_vendor_shipment_status"),
        ("ix_vendor_shipment_updates_status", "ix_vendor_ship_update_status"),
        ("ix_vendor_shipment_updates_shipment_id", "ix_vendor_ship_update_shipment_id"),
        ("ix_vendor_shipment_updates_inbound_event_id", "ix_vendor_ship_update_inbound_event_id"),
        ("ix_vendor_inbound_events_import_run_id", "ix_vendor_event_import_run"),
        ("ix_vendor_connector_schedules_next_run_at", "ix_vendor_schedule_next_run"),
        ("ix_vendor_connector_schedules_endpoint_id", "ix_vendor_schedule_endpoint"),
        ("ix_vendor_connector_schedules_is_enabled", "ix_vendor_schedule_enabled"),
        ("ix_vendor_connector_import_runs_status", "ix_vendor_import_status"),
        ("ix_vendor_connector_import_runs_endpoint_id", "ix_vendor_import_endpoint"),
        ("ix_vendor_connector_import_runs_content_sha256", "ix_vendor_import_checksum"),
        ("ix_vendor_connector_executions_status", "ix_vendor_execution_status"),
        ("ix_vendor_connector_executions_schedule_id", "ix_vendor_execution_schedule"),
        ("ix_vendor_connector_executions_endpoint_id", "ix_vendor_execution_endpoint"),
        ("ix_vendor_connector_executions_available_at", "ix_vendor_execution_available"),
        ("ix_vendor_advance_ship_notices_vendor_code", "ix_vendor_asn_vendor_code"),
        ("ix_vendor_advance_ship_notices_status", "ix_vendor_asn_status"),
        ("ix_vendor_advance_ship_notices_shipment_id", "ix_vendor_asn_shipment_id"),
        ("ix_vendor_advance_ship_notices_inbound_event_id", "ix_vendor_asn_inbound_event_id"),
        (
            "ix_vendor_advance_ship_notice_lines_asn_id",
            "ix_vendor_asn_line_asn_id",
        ),
    ):
        op.execute(f"ALTER INDEX {new_name} RENAME TO {old_name}")

    for table, column in (
        ("vendor_shipments", "updated_at"),
        ("vendor_shipments", "created_at"),
        ("vendor_shipment_updates", "created_at"),
        ("vendor_inbound_events", "received_at"),
        ("vendor_endpoints", "updated_at"),
        ("vendor_endpoints", "created_at"),
        ("vendor_connector_schedules", "updated_at"),
        ("vendor_connector_schedules", "created_at"),
        ("vendor_connector_import_runs", "created_at"),
        ("vendor_connector_executions", "created_at"),
        ("vendor_advance_ship_notices", "created_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            existing_server_default=sa.text("now()"),
        )
