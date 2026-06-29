import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.models.event_snapshot import EventSnapshot
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.vendor_integration import (
    VendorConnectorExecution,
    VendorConnectorImportRun,
    VendorEndpoint,
    VendorInboundEvent,
    VendorPurchaseOrderAcknowledgement,
)
from app.schemas.vendor_integration import (
    VendorAcknowledgementPayload,
    VendorConnectorExecutionResult,
    VendorConnectorScheduleCreate,
    VendorEndpointCreate,
    VendorEndpointDirection,
    VendorEventType,
    VendorInboundEventCreate,
    VendorTransport,
)
from app.services.vendor_acknowledgement_service import (
    VendorAcknowledgementError,
    process_vendor_acknowledgement,
)
from app.services.vendor_connector_import_service import (
    VendorConnectorImportError,
    import_vendor_events,
)
from app.services.vendor_connector_operations_service import (
    VendorConnectorOperationsError,
    claim_connector_execution,
    complete_connector_execution,
    create_connector_schedule,
    enqueue_due_connector_executions,
    replay_dead_letter,
)
from app.services.vendor_integration_service import (
    VendorIntegrationError,
    create_vendor_endpoint,
    ingest_vendor_event,
    list_vendor_events,
)
from app.services.vendor_shipment_service import (
    VendorShipmentError,
    process_asn,
    process_shipment_update,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            CatalogVendor(
                vendor_code="V-001",
                name="Integration Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        session.commit()
        yield session


def _endpoint_payload(
    direction: VendorEndpointDirection = VendorEndpointDirection.INBOUND,
    name: str = "Primary inbound",
) -> VendorEndpointCreate:
    return VendorEndpointCreate(
        vendor_code="V-001",
        name=name,
        transport=VendorTransport.REST_API,
        direction=direction,
        connection_reference="vault://vendors/v-001/api",
        configuration={"base_url": "https://vendor.invalid"},
    )


def _event_payload(endpoint_id: str, payload: dict | None = None) -> VendorInboundEventCreate:
    return VendorInboundEventCreate(
        endpoint_id=endpoint_id,
        external_event_id="vendor-event-001",
        event_type=VendorEventType.ACKNOWLEDGEMENT,
        payload=payload or {"purchase_order": "PO-001", "accepted": True},
    )


def _purchase_order(db: Session, vendor_code: str = "V-001", status: str = "transmitted"):
    order = PurchaseOrder(
        po_number=f"PO-ACK-{vendor_code}",
        workflow_code="BPP_PURCHASING",
        vendor_code=vendor_code,
        status=status,
        currency="USD",
        subtotal=100,
        freight_total=0,
        tax_total=0,
        total=100,
        created_by="admin@example.com",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _acknowledgement_event(
    db: Session,
    endpoint: VendorEndpoint,
    order: PurchaseOrder,
    outcome: str = "accepted",
    **details,
) -> VendorInboundEvent:
    event, _created = ingest_vendor_event(
        db,
        VendorInboundEventCreate(
            endpoint_id=endpoint.id,
            external_event_id=f"ACK-{order.po_number}-{outcome}",
            event_type=VendorEventType.ACKNOWLEDGEMENT,
            payload={
                "purchase_order_number": order.po_number,
                "acknowledgement_status": outcome,
                **details,
            },
        ),
        "integration@example.com",
    )
    return event


def test_endpoint_creation_requires_active_catalog_vendor_and_writes_snapshot(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")

    assert endpoint.vendor_code == "V-001"
    assert endpoint.connection_reference == "vault://vendors/v-001/api"
    assert db.scalar(select(func.count()).select_from(VendorEndpoint)) == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(EventSnapshot.event_type == "vendor.endpoint_created")
        )
        == 1
    )

    db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == "V-001")).is_active = False
    db.commit()
    with pytest.raises(VendorIntegrationError, match="not active"):
        create_vendor_endpoint(db, _endpoint_payload(name="Secondary"), "admin@example.com")


def test_inbound_event_is_canonical_idempotent_and_audited(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")

    first, first_created = ingest_vendor_event(
        db,
        _event_payload(endpoint.id, {"accepted": True, "purchase_order": "PO-001"}),
        "integration@example.com",
    )
    repeated, repeated_created = ingest_vendor_event(
        db,
        _event_payload(endpoint.id, {"purchase_order": "PO-001", "accepted": True}),
        "integration@example.com",
    )

    assert first_created is True
    assert repeated_created is False
    assert repeated.id == first.id
    assert first.status == "received"
    assert len(first.payload_sha256) == 64
    assert db.scalar(select(func.count()).select_from(VendorInboundEvent)) == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(EventSnapshot)
            .where(EventSnapshot.event_type == "vendor.inbound_event_received")
        )
        == 1
    )


def test_external_event_id_conflict_fails_closed(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    ingest_vendor_event(db, _event_payload(endpoint.id), "integration@example.com")

    with pytest.raises(VendorIntegrationError, match="different event content"):
        ingest_vendor_event(
            db,
            _event_payload(endpoint.id, {"purchase_order": "PO-001", "accepted": False}),
            "integration@example.com",
        )


def test_outbound_endpoint_rejects_inbound_events(db: Session) -> None:
    endpoint = create_vendor_endpoint(
        db,
        _endpoint_payload(direction=VendorEndpointDirection.OUTBOUND),
        "admin@example.com",
    )

    with pytest.raises(VendorIntegrationError, match="does not accept inbound"):
        ingest_vendor_event(db, _event_payload(endpoint.id), "integration@example.com")


def test_event_filters_remain_vendor_and_endpoint_scoped(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    event, _created = ingest_vendor_event(
        db, _event_payload(endpoint.id), "integration@example.com"
    )

    assert list_vendor_events(db, vendor_code="V-001") == [event]
    assert list_vendor_events(db, endpoint_id="missing") == []
    assert list_vendor_events(db, event_type="asn") == []


@pytest.mark.parametrize(
    "configuration",
    [
        {"password": "embedded"},
        {"auth": {"api_key": "embedded"}},
        {"headers": [{"token": "embedded"}]},
        {"headers": {"Authorization": "Bearer embedded"}},
        {"client-secret": "embedded"},
        {"base_url": "https://user:password@vendor.invalid/events"},
    ],
)
def test_endpoint_configuration_rejects_embedded_secrets(configuration: dict) -> None:
    with pytest.raises(ValidationError, match="must not contain connector secrets"):
        VendorEndpointCreate(
            vendor_code="V-001",
            name="Unsafe endpoint",
            transport=VendorTransport.REST_API,
            direction=VendorEndpointDirection.INBOUND,
            configuration=configuration,
        )


def test_endpoint_response_model_inputs_are_enum_constrained() -> None:
    with pytest.raises(ValidationError):
        VendorEndpointCreate(
            vendor_code="V-001",
            name="Unknown transport",
            transport="webhook",  # type: ignore[arg-type]
            direction=VendorEndpointDirection.INBOUND,
        )


def test_json_connector_import_creates_linked_events_and_is_checksum_idempotent(
    db: Session,
) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    content = json.dumps(
        [
            {
                "external_event_id": "import-1",
                "event_type": "acknowledgement",
                "payload": {"ok": True},
            },
            {"external_event_id": "import-2", "event_type": "asn", "payload": {"lines": []}},
        ]
    ).encode()

    run, created = import_vendor_events(
        db, endpoint.id, content, "vendor-events.json", "application/json", "admin@example.com"
    )
    repeated, repeated_created = import_vendor_events(
        db, endpoint.id, content, "renamed.json", "application/json", "admin@example.com"
    )

    assert created is True
    assert repeated_created is False
    assert repeated.id == run.id
    assert run.status == "completed"
    assert run.event_count == 2
    assert len(run.content_sha256) == 64
    events = list_vendor_events(db, endpoint_id=endpoint.id)
    assert {event.import_run_id for event in events} == {run.id}
    assert db.scalar(select(func.count()).select_from(VendorConnectorImportRun)) == 1


@pytest.mark.parametrize(
    ("content", "content_type", "message"),
    [
        (b"", "application/json", "empty"),
        (b"not-json", "application/json", "valid normalized"),
        (b"[]", "application/json", "at least one"),
        (b"{}", "text/csv", "content type must be JSON"),
    ],
)
def test_connector_import_rejects_invalid_input(
    db: Session, content: bytes, content_type: str, message: str
) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    with pytest.raises(VendorConnectorImportError, match=message):
        import_vendor_events(
            db, endpoint.id, content, "events.json", content_type, "admin@example.com"
        )


def test_edi_connector_import_fails_closed_without_mapping(db: Session) -> None:
    payload = _endpoint_payload()
    payload.transport = VendorTransport.EDI
    endpoint = create_vendor_endpoint(db, payload, "admin@example.com")

    with pytest.raises(VendorConnectorImportError, match="transaction-set mapping"):
        import_vendor_events(
            db,
            endpoint.id,
            b"ISA*00*...~",
            "ack.edi",
            "application/edi-x12",
            "admin@example.com",
        )


def test_connector_import_reports_partial_event_conflict(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    ingest_vendor_event(db, _event_payload(endpoint.id), "admin@example.com")
    content = json.dumps(
        [
            {"external_event_id": "fresh", "event_type": "asn", "payload": {"ok": True}},
            {
                "external_event_id": "vendor-event-001",
                "event_type": "acknowledgement",
                "payload": {"accepted": False},
            },
        ]
    ).encode()

    run, created = import_vendor_events(
        db, endpoint.id, content, "events.json", "application/json", "admin@example.com"
    )

    assert created is True
    assert run.status == "failed"
    assert run.event_count == 1
    assert "different event content" in (run.error_message or "")


def test_connector_execution_retries_dead_letters_and_replays(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)
    schedule = create_connector_schedule(
        db,
        VendorConnectorScheduleCreate(
            endpoint_id=endpoint.id,
            name="Every hour",
            interval_minutes=60,
            max_attempts=2,
            base_retry_seconds=5,
            next_run_at=now,
        ),
        "admin@example.com",
    )

    queued = enqueue_due_connector_executions(db, "scheduler@example.com", now)
    assert len(queued) == 1
    assert enqueue_due_connector_executions(db, "scheduler@example.com", now) == []
    assert schedule.next_run_at.replace(tzinfo=UTC) == now + timedelta(hours=1)

    first, first_token = claim_connector_execution(db, "worker-1", 30, now) or (None, None)
    assert first is not None and first_token is not None
    assert first.status == "running"
    assert first.attempt_count == 1
    stored = db.get(VendorConnectorExecution, first.id)
    assert stored is not None
    assert stored.lease_token_hash is not None
    assert stored.lease_token_hash != first_token
    retry = complete_connector_execution(
        db,
        first.id,
        VendorConnectorExecutionResult(
            lease_token=first_token,
            succeeded=False,
            error_message="SFTP unavailable",
        ),
        "worker@example.com",
        now,
    )
    assert retry.status == "retry"
    assert retry.available_at.replace(tzinfo=UTC) == now + timedelta(seconds=5)

    second, second_token = claim_connector_execution(
        db, "worker-2", 30, now + timedelta(seconds=5)
    ) or (None, None)
    assert second is not None and second_token is not None
    dead = complete_connector_execution(
        db,
        second.id,
        VendorConnectorExecutionResult(
            lease_token=second_token,
            succeeded=False,
            error_message="SFTP still unavailable",
        ),
        "worker@example.com",
        now + timedelta(seconds=5),
    )
    assert dead.status == "dead_letter"
    assert dead.attempt_count == 2

    replayed = replay_dead_letter(db, dead.id, "operator@example.com", now)
    assert replayed.status == "queued"
    assert replayed.attempt_count == 0
    assert replayed.error_message is None


def test_connector_execution_enforces_lease_and_expires_abandoned_work(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)
    create_connector_schedule(
        db,
        VendorConnectorScheduleCreate(
            endpoint_id=endpoint.id,
            name="One attempt",
            interval_minutes=60,
            max_attempts=1,
            next_run_at=now,
        ),
        "admin@example.com",
    )
    execution = enqueue_due_connector_executions(db, "scheduler@example.com", now)[0]
    claimed, token = claim_connector_execution(db, "worker-1", 30, now) or (None, None)
    assert claimed is not None and token is not None

    with pytest.raises(VendorConnectorOperationsError, match="token is invalid"):
        complete_connector_execution(
            db,
            execution.id,
            VendorConnectorExecutionResult(
                lease_token="0" * 64,
                succeeded=True,
            ),
            "worker@example.com",
            now,
        )

    assert claim_connector_execution(db, "worker-2", 30, now + timedelta(seconds=31)) is None
    db.refresh(execution)
    assert execution.status == "dead_letter"
    assert execution.error_message == "Worker lease expired"


def test_connector_worker_rejects_legacy_embedded_credentials(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    now = datetime(2026, 6, 28, 12, tzinfo=UTC)
    create_connector_schedule(
        db,
        VendorConnectorScheduleCreate(
            endpoint_id=endpoint.id,
            name="Unsafe legacy endpoint",
            interval_minutes=60,
            next_run_at=now,
        ),
        "admin@example.com",
    )
    execution = enqueue_due_connector_executions(db, "scheduler@example.com", now)[0]
    endpoint.configuration = {"headers": {"authorization": "Bearer legacy-secret"}}
    db.commit()

    assert claim_connector_execution(db, "worker-1", 30, now) is None
    db.refresh(execution)
    assert execution.status == "dead_letter"
    assert "prohibited credential material" in (execution.error_message or "")


def test_accepted_acknowledgement_projects_purchase_order_and_is_idempotent(
    db: Session,
) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db)
    event = _acknowledgement_event(
        db,
        endpoint,
        order,
        vendor_reference="VENDOR-ACK-001",
    )

    acknowledgement, created = process_vendor_acknowledgement(db, event.id, "admin@example.com")
    repeated, repeated_created = process_vendor_acknowledgement(db, event.id, "admin@example.com")

    db.refresh(order)
    db.refresh(event)
    assert created is True
    assert repeated_created is False
    assert repeated.id == acknowledgement.id
    assert acknowledgement.acknowledgement_status == "accepted"
    assert order.status == "vendor_acknowledged"
    assert event.status == "processed"
    assert db.scalar(select(func.count()).select_from(VendorPurchaseOrderAcknowledgement)) == 1


@pytest.mark.parametrize(
    ("outcome", "details", "expected_order_status"),
    [
        (
            "accepted_with_changes",
            {"changes": [{"field": "quantity", "requested": "2", "accepted": "1"}]},
            "vendor_acknowledged_changes",
        ),
        ("rejected", {"reason": "Item is discontinued"}, "vendor_rejected"),
    ],
)
def test_acknowledgement_outcomes_project_exception_states(
    db: Session, outcome: str, details: dict, expected_order_status: str
) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db)
    event = _acknowledgement_event(db, endpoint, order, outcome, **details)

    acknowledgement, _created = process_vendor_acknowledgement(db, event.id, "admin@example.com")

    db.refresh(order)
    assert acknowledgement.acknowledgement_status == outcome
    assert order.status == expected_order_status


def test_acknowledgement_rejects_cross_vendor_purchase_order(db: Session) -> None:
    db.add(
        CatalogVendor(
            vendor_code="V-002",
            name="Other Vendor",
            is_active=True,
            source_file="test.xlsx",
        )
    )
    db.commit()
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db, vendor_code="V-002")
    event = _acknowledgement_event(db, endpoint, order)

    with pytest.raises(VendorAcknowledgementError, match="does not match"):
        process_vendor_acknowledgement(db, event.id, "admin@example.com")

    db.refresh(event)
    db.refresh(order)
    assert event.status == "rejected"
    assert order.status == "transmitted"


def test_acknowledgement_requires_completed_internal_transmission(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db, status="transmission_ready")
    event = _acknowledgement_event(db, endpoint, order)

    with pytest.raises(VendorAcknowledgementError, match="not completed"):
        process_vendor_acknowledgement(db, event.id, "admin@example.com")

    db.refresh(event)
    assert event.status == "rejected"


@pytest.mark.parametrize(
    "payload",
    [
        {"purchase_order_number": "PO-1", "acknowledgement_status": "rejected"},
        {
            "purchase_order_number": "PO-1",
            "acknowledgement_status": "accepted_with_changes",
        },
    ],
)
def test_acknowledgement_payload_requires_exception_details(payload: dict) -> None:
    with pytest.raises(ValidationError):
        VendorAcknowledgementPayload.model_validate(payload)


def test_shipment_updates_create_and_advance_vendor_logistics(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db, status="vendor_acknowledged")

    def event(number: str, shipment_status: str):
        item, _ = ingest_vendor_event(
            db,
            VendorInboundEventCreate(
                endpoint_id=endpoint.id,
                external_event_id=number,
                event_type=VendorEventType.SHIPMENT_UPDATE,
                payload={
                    "purchase_order_number": order.po_number,
                    "shipment_number": "SHIP-001",
                    "status": shipment_status,
                    "carrier": "Test Carrier",
                },
            ),
            "integration@example.com",
        )
        return item

    planned, created = process_shipment_update(db, event("SHIP-E1", "planned").id, "admin")
    transit, _ = process_shipment_update(db, event("SHIP-E2", "in_transit").id, "admin")
    replay, replay_created = process_shipment_update(db, "" + transit.inbound_event_id, "admin")

    db.refresh(order)
    assert created is True
    assert replay_created is False
    assert planned.shipment_id == transit.shipment_id == replay.shipment_id
    assert order.status == "shipment_in_transit"


def test_asn_enforces_po_line_and_cumulative_quantity(db: Session) -> None:
    endpoint = create_vendor_endpoint(db, _endpoint_payload(), "admin@example.com")
    order = _purchase_order(db, status="vendor_acknowledged")
    line = PurchaseOrderLine(
        purchase_order_id=order.id,
        source_request_id="validation-source",
        source_line_id=1,
        store_number="1001",
        product_code="P-001",
        product_name="Product",
        quantity=2,
        unit_price=50,
        freight_amount=0,
        tax_amount=0,
        extended_amount=100,
    )
    db.add(line)
    db.commit()

    def event(external_id: str, quantity: float):
        item, _ = ingest_vendor_event(
            db,
            VendorInboundEventCreate(
                endpoint_id=endpoint.id,
                external_event_id=external_id,
                event_type=VendorEventType.ASN,
                payload={
                    "purchase_order_number": order.po_number,
                    "asn_number": external_id,
                    "lines": [
                        {
                            "purchase_order_line_id": line.id,
                            "product_code": line.product_code,
                            "quantity": quantity,
                        }
                    ],
                },
            ),
            "integration@example.com",
        )
        return item

    asn, created = process_asn(db, event("ASN-001", 1.5).id, "admin")
    assert created is True
    assert len(asn.lines) == 1

    second = event("ASN-002", 1)
    with pytest.raises(VendorShipmentError, match="exceeds ordered"):
        process_asn(db, second.id, "admin")
    db.refresh(second)
    assert second.status == "rejected"
