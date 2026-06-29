import hashlib
import json
from datetime import UTC, datetime

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.vendor_integration import VendorConnectorImportRun, VendorEndpoint
from app.schemas.vendor_integration import VendorImportEvent, VendorInboundEventCreate
from app.services.vendor_integration_service import VendorIntegrationError, ingest_vendor_event

MAX_CONNECTOR_IMPORT_BYTES = 10 * 1024 * 1024
_JSON_TYPES = {"application/json", "text/json"}
_IMPORT_EVENTS = TypeAdapter(VendorImportEvent | list[VendorImportEvent])


class VendorConnectorImportError(ValueError):
    pass


def _translate_json(content: bytes) -> list[VendorImportEvent]:
    try:
        document = json.loads(content)
        parsed = _IMPORT_EVENTS.validate_python(document)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise VendorConnectorImportError(
            "Import must contain valid normalized vendor event JSON"
        ) from exc
    events = parsed if isinstance(parsed, list) else [parsed]
    if not events:
        raise VendorConnectorImportError("Import must contain at least one vendor event")
    if len(events) > 1000:
        raise VendorConnectorImportError("Import exceeds the 1000-event limit")
    return events


def _translate(
    endpoint: VendorEndpoint, content: bytes, content_type: str | None
) -> list[VendorImportEvent]:
    media_type = (content_type or "").partition(";")[0].strip().lower()
    if endpoint.transport == "edi":
        raise VendorConnectorImportError(
            "EDI translation is not configured; an explicit transaction-set mapping is required"
        )
    if endpoint.transport not in {"rest_api", "sftp", "manual_import"}:
        raise VendorConnectorImportError("Endpoint transport does not support connector imports")
    if media_type and media_type not in _JSON_TYPES and not media_type.endswith("+json"):
        raise VendorConnectorImportError("Connector import content type must be JSON")
    return _translate_json(content)


def import_vendor_events(
    db: Session,
    endpoint_id: str,
    content: bytes,
    source_name: str,
    content_type: str | None,
    actor: str,
) -> tuple[VendorConnectorImportRun, bool]:
    endpoint = db.get(VendorEndpoint, endpoint_id)
    if endpoint is None or not endpoint.is_active:
        raise VendorConnectorImportError("Vendor endpoint is not active")
    if endpoint.direction not in {"inbound", "bidirectional"}:
        raise VendorConnectorImportError("Vendor endpoint does not accept inbound imports")
    if not content:
        raise VendorConnectorImportError("Connector import file is empty")
    if len(content) > MAX_CONNECTOR_IMPORT_BYTES:
        raise VendorConnectorImportError("Connector import exceeds the 10 MiB limit")

    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(VendorConnectorImportRun).where(
            VendorConnectorImportRun.endpoint_id == endpoint_id,
            VendorConnectorImportRun.content_sha256 == digest,
        )
    )
    if existing is not None:
        return existing, False

    events = _translate(endpoint, content, content_type)
    run = VendorConnectorImportRun(
        endpoint_id=endpoint_id,
        source_name=(source_name or "import.json")[:255],
        content_type=(content_type or None),
        content_sha256=digest,
        status="processing",
        imported_by=actor,
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(VendorConnectorImportRun).where(
                VendorConnectorImportRun.endpoint_id == endpoint_id,
                VendorConnectorImportRun.content_sha256 == digest,
            )
        )
        if existing is not None:
            return existing, False
        raise
    db.refresh(run)

    try:
        for item in events:
            _event, created = ingest_vendor_event(
                db,
                VendorInboundEventCreate(endpoint_id=endpoint_id, **item.model_dump()),
                actor,
                import_run_id=run.id,
            )
            run.event_count += int(created)
        run.status = "completed"
    except VendorIntegrationError as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
    run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run, True


def list_connector_import_runs(
    db: Session, endpoint_id: str | None = None
) -> list[VendorConnectorImportRun]:
    statement = select(VendorConnectorImportRun).order_by(
        VendorConnectorImportRun.created_at.desc()
    )
    if endpoint_id is not None:
        statement = statement.where(VendorConnectorImportRun.endpoint_id == endpoint_id)
    return list(db.scalars(statement).all())
