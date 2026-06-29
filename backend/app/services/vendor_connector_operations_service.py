import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.vendor_integration import (
    VendorConnectorExecution,
    VendorConnectorImportRun,
    VendorConnectorSchedule,
    VendorEndpoint,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.vendor_integration import (
    VendorConnectorExecutionResult,
    VendorConnectorScheduleCreate,
    VendorConnectorScheduleUpdate,
)
from app.services.snapshot_service import append_snapshot
from app.services.vendor_connector_security import configuration_contains_secret


class VendorConnectorOperationsError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _lease_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def create_connector_schedule(
    db: Session, payload: VendorConnectorScheduleCreate, actor: str
) -> VendorConnectorSchedule:
    endpoint = db.get(VendorEndpoint, payload.endpoint_id)
    if endpoint is None or not endpoint.is_active:
        raise VendorConnectorOperationsError("Vendor endpoint is not active")
    if endpoint.direction not in {"inbound", "bidirectional"}:
        raise VendorConnectorOperationsError("Vendor endpoint does not accept inbound work")
    schedule = VendorConnectorSchedule(
        **payload.model_dump(exclude={"next_run_at"}),
        next_run_at=payload.next_run_at or _now(),
        created_by=actor,
        updated_by=actor,
    )
    db.add(schedule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise VendorConnectorOperationsError(
            "A connector schedule with this endpoint and name already exists"
        ) from exc
    db.refresh(schedule)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.connector_schedule_created",
            entity_type="vendor_connector_schedule",
            entity_id=schedule.id,
            actor=actor,
            payload={
                "endpoint_id": schedule.endpoint_id,
                "interval_minutes": schedule.interval_minutes,
                "max_attempts": schedule.max_attempts,
            },
        ),
    )
    return schedule


def list_connector_schedules(db: Session) -> list[VendorConnectorSchedule]:
    return list(
        db.scalars(select(VendorConnectorSchedule).order_by(VendorConnectorSchedule.name)).all()
    )


def update_connector_schedule(
    db: Session,
    schedule_id: str,
    payload: VendorConnectorScheduleUpdate,
    actor: str,
) -> VendorConnectorSchedule:
    schedule = db.get(VendorConnectorSchedule, schedule_id)
    if schedule is None:
        raise VendorConnectorOperationsError("Connector schedule not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(schedule, field, value)
    schedule.updated_by = actor
    db.commit()
    db.refresh(schedule)
    return schedule


def enqueue_due_connector_executions(
    db: Session, actor: str, now: datetime | None = None
) -> list[VendorConnectorExecution]:
    current = now or _now()
    schedules = list(
        db.scalars(
            select(VendorConnectorSchedule)
            .where(
                VendorConnectorSchedule.is_enabled.is_(True),
                VendorConnectorSchedule.next_run_at <= current,
            )
            .order_by(VendorConnectorSchedule.next_run_at)
            .with_for_update(skip_locked=True)
        ).all()
    )
    executions: list[VendorConnectorExecution] = []
    for schedule in schedules:
        scheduled_for = schedule.next_run_at
        execution = VendorConnectorExecution(
            schedule_id=schedule.id,
            endpoint_id=schedule.endpoint_id,
            status="queued",
            scheduled_for=scheduled_for,
            available_at=current,
            max_attempts=schedule.max_attempts,
            base_retry_seconds=schedule.base_retry_seconds,
        )
        db.add(execution)
        schedule.next_run_at = current + timedelta(minutes=schedule.interval_minutes)
        schedule.updated_by = actor
        executions.append(execution)
    db.commit()
    for execution in executions:
        db.refresh(execution)
    return executions


def _expire_leases(db: Session, current: datetime) -> None:
    expired = list(
        db.scalars(
            select(VendorConnectorExecution).where(
                VendorConnectorExecution.status == "running",
                VendorConnectorExecution.lease_expires_at <= current,
            )
        ).all()
    )
    for execution in expired:
        execution.lease_token_hash = None
        execution.lease_expires_at = None
        execution.worker_id = None
        execution.error_message = "Worker lease expired"
        if execution.attempt_count >= execution.max_attempts:
            execution.status = "dead_letter"
            execution.completed_at = current
        else:
            execution.status = "retry"
            delay = execution.base_retry_seconds * 2 ** (execution.attempt_count - 1)
            execution.available_at = current + timedelta(seconds=delay)


def claim_connector_execution(
    db: Session,
    worker_id: str,
    lease_seconds: int,
    now: datetime | None = None,
) -> tuple[VendorConnectorExecution, str] | None:
    current = now or _now()
    _expire_leases(db, current)
    execution = db.scalar(
        select(VendorConnectorExecution)
        .where(
            VendorConnectorExecution.status.in_(("queued", "retry")),
            VendorConnectorExecution.available_at <= current,
        )
        .order_by(VendorConnectorExecution.available_at, VendorConnectorExecution.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if execution is None:
        db.commit()
        return None
    endpoint = db.get(VendorEndpoint, execution.endpoint_id)
    if endpoint is None or not endpoint.is_active:
        execution.status = "dead_letter"
        execution.error_message = "Vendor endpoint is not active"
        execution.completed_at = current
        db.commit()
        return None
    if configuration_contains_secret(endpoint.configuration):
        execution.status = "dead_letter"
        execution.error_message = "Endpoint configuration contains prohibited credential material"
        execution.completed_at = current
        db.commit()
        return None
    token = secrets.token_hex(32)
    execution.status = "running"
    execution.attempt_count += 1
    execution.worker_id = worker_id
    execution.lease_token_hash = _lease_digest(token)
    execution.lease_expires_at = current + timedelta(seconds=lease_seconds)
    execution.started_at = current
    execution.completed_at = None
    db.commit()
    db.refresh(execution)
    return execution, token


def complete_connector_execution(
    db: Session,
    execution_id: str,
    payload: VendorConnectorExecutionResult,
    actor: str,
    now: datetime | None = None,
) -> VendorConnectorExecution:
    current = now or _now()
    execution = db.get(VendorConnectorExecution, execution_id)
    if execution is None:
        raise VendorConnectorOperationsError("Connector execution not found")
    if execution.status != "running" or execution.lease_token_hash is None:
        raise VendorConnectorOperationsError("Connector execution does not have an active lease")
    if not secrets.compare_digest(execution.lease_token_hash, _lease_digest(payload.lease_token)):
        raise VendorConnectorOperationsError("Connector execution lease token is invalid")
    expires_at = execution.lease_expires_at
    if expires_at is None or expires_at.replace(tzinfo=expires_at.tzinfo or UTC) <= current:
        raise VendorConnectorOperationsError("Connector execution lease has expired")
    if payload.import_run_id is not None:
        import_run = db.get(VendorConnectorImportRun, payload.import_run_id)
        if import_run is None or import_run.endpoint_id != execution.endpoint_id:
            raise VendorConnectorOperationsError("Import run does not belong to this endpoint")
        if payload.succeeded and import_run.status != "completed":
            raise VendorConnectorOperationsError(
                "Successful execution requires a completed import run"
            )

    execution.lease_token_hash = None
    execution.lease_expires_at = None
    if payload.succeeded:
        execution.status = "completed"
        execution.import_run_id = payload.import_run_id
        execution.error_message = None
        execution.completed_at = current
    else:
        execution.error_message = payload.error_message
        if execution.attempt_count >= execution.max_attempts:
            execution.status = "dead_letter"
            execution.completed_at = current
        else:
            execution.status = "retry"
            delay = execution.base_retry_seconds * 2 ** (execution.attempt_count - 1)
            execution.available_at = current + timedelta(seconds=delay)
    db.commit()
    db.refresh(execution)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type=f"vendor.connector_execution_{execution.status}",
            entity_type="vendor_connector_execution",
            entity_id=execution.id,
            actor=actor,
            payload={
                "endpoint_id": execution.endpoint_id,
                "attempt_count": execution.attempt_count,
                "import_run_id": execution.import_run_id,
            },
        ),
    )
    return execution


def replay_dead_letter(
    db: Session, execution_id: str, actor: str, now: datetime | None = None
) -> VendorConnectorExecution:
    execution = db.get(VendorConnectorExecution, execution_id)
    if execution is None or execution.status != "dead_letter":
        raise VendorConnectorOperationsError("Only dead-letter executions can be replayed")
    execution.status = "queued"
    execution.attempt_count = 0
    execution.available_at = now or _now()
    execution.worker_id = None
    execution.lease_token_hash = None
    execution.lease_expires_at = None
    execution.error_message = None
    execution.completed_at = None
    db.commit()
    db.refresh(execution)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="vendor.connector_execution_replayed",
            entity_type="vendor_connector_execution",
            entity_id=execution.id,
            actor=actor,
            payload={"endpoint_id": execution.endpoint_id},
        ),
    )
    return execution


def list_connector_executions(
    db: Session, status: str | None = None
) -> list[VendorConnectorExecution]:
    statement = select(VendorConnectorExecution).order_by(
        VendorConnectorExecution.created_at.desc()
    )
    if status is not None:
        statement = statement.where(VendorConnectorExecution.status == status)
    return list(db.scalars(statement).all())
