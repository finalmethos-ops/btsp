import csv
import hashlib
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsReportRun, AnalyticsReportSchedule
from app.schemas.analytics import (
    AnalyticsReportScheduleCreate,
    AnalyticsReportType,
    SpendDimension,
)
from app.services.analytics_service import (
    inventory_positions,
    spend_analysis,
    vendor_scorecards,
    workflow_analytics,
)


class AnalyticsReportError(ValueError):
    pass


def _csv_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows([[_safe_csv_cell(cell) for cell in row] for row in rows])
    return stream.getvalue().encode("utf-8")


def _safe_csv_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def render_analytics_report(
    db: Session, report_type: AnalyticsReportType, parameters: dict[str, str]
) -> bytes:
    if report_type is AnalyticsReportType.INVENTORY_POSITION:
        result = inventory_positions(
            db,
            store_number=parameters.get("store_number"),
            product_code=parameters.get("product_code"),
        )
        return _csv_bytes(
            [
                "store_number",
                "product_code",
                "product_name",
                "accepted_quantity",
                "rejected_quantity",
                "outstanding_backorder_quantity",
            ],
            [
                [
                    item.store_number,
                    item.product_code,
                    item.product_name,
                    item.accepted_quantity,
                    item.rejected_quantity,
                    item.outstanding_backorder_quantity,
                ]
                for item in result.positions
            ],
        )
    if report_type is AnalyticsReportType.SPEND:
        try:
            dimension = SpendDimension(parameters.get("group_by", "vendor"))
        except ValueError as exc:
            raise AnalyticsReportError("Spend report group_by parameter is invalid") from exc
        result = spend_analysis(
            db,
            dimension,
            vendor_code=parameters.get("vendor_code"),
            store_number=parameters.get("store_number"),
            workflow_code=parameters.get("workflow_code"),
        )
        return _csv_bytes(
            [
                "dimension_key",
                "currency",
                "purchase_order_count",
                "line_count",
                "quantity",
                "amount",
            ],
            [
                [
                    item.dimension_key,
                    item.currency,
                    item.purchase_order_count,
                    item.line_count,
                    item.quantity,
                    item.amount,
                ]
                for item in result.metrics
            ],
        )
    if report_type is AnalyticsReportType.VENDOR_SCORECARDS:
        result = vendor_scorecards(db, minimum_orders=int(parameters.get("minimum_orders", "1")))
        return _csv_bytes(
            [
                "vendor_code",
                "vendor_name",
                "purchase_order_count",
                "acknowledgement_coverage_rate",
                "on_time_delivery_rate",
                "receiving_acceptance_rate",
                "invoice_match_rate",
            ],
            [
                [
                    item.vendor_code,
                    item.vendor_name,
                    item.purchase_order_count,
                    item.acknowledgement_coverage_rate,
                    item.on_time_delivery_rate,
                    item.receiving_acceptance_rate,
                    item.invoice_match_rate,
                ]
                for item in result.scorecards
            ],
        )
    result = workflow_analytics(db, workflow_code=parameters.get("workflow_code"))
    return _csv_bytes(
        [
            "workflow_code",
            "instance_count",
            "active_count",
            "completed_count",
            "transition_count",
            "approval_count",
            "rejection_count",
            "average_completion_seconds",
            "median_completion_seconds",
            "p90_completion_seconds",
        ],
        [
            [
                item.workflow_code,
                item.instance_count,
                item.active_count,
                item.completed_count,
                item.transition_count,
                item.approval_count,
                item.rejection_count,
                item.average_completion_seconds,
                item.median_completion_seconds,
                item.p90_completion_seconds,
            ]
            for item in result.workflows
        ],
    )


def create_report_schedule(
    db: Session, payload: AnalyticsReportScheduleCreate, actor: str
) -> AnalyticsReportSchedule:
    schedule = AnalyticsReportSchedule(
        **payload.model_dump(exclude={"next_run_at"}, mode="json"),
        next_run_at=payload.next_run_at or datetime.now(UTC),
        created_by=actor,
        updated_by=actor,
    )
    db.add(schedule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AnalyticsReportError("A report schedule with this name already exists") from exc
    db.refresh(schedule)
    return schedule


def list_report_schedules(db: Session, limit: int = 100) -> list[AnalyticsReportSchedule]:
    return list(
        db.scalars(
            select(AnalyticsReportSchedule).order_by(AnalyticsReportSchedule.name).limit(limit)
        ).all()
    )


def list_report_runs(db: Session, limit: int = 100) -> list[AnalyticsReportRun]:
    return list(
        db.scalars(
            select(AnalyticsReportRun).order_by(AnalyticsReportRun.created_at.desc()).limit(limit)
        ).all()
    )


def run_due_reports(
    db: Session, actor: str, storage_root: str, now: datetime | None = None
) -> list[AnalyticsReportRun]:
    current = now or datetime.now(UTC)
    schedules = list(
        db.scalars(
            select(AnalyticsReportSchedule)
            .where(
                AnalyticsReportSchedule.is_enabled.is_(True),
                AnalyticsReportSchedule.next_run_at <= current,
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    root = Path(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    runs: list[AnalyticsReportRun] = []
    for schedule in schedules:
        run = AnalyticsReportRun(
            schedule_id=schedule.id,
            scheduled_for=schedule.next_run_at,
            status="processing",
            created_by=actor,
        )
        db.add(run)
        schedule.next_run_at = current + timedelta(minutes=schedule.interval_minutes)
        schedule.updated_by = actor
        db.flush()
        try:
            content = render_analytics_report(
                db, AnalyticsReportType(schedule.report_type), schedule.parameters
            )
            filename = f"{run.id}.csv"
            (root / filename).write_bytes(content)
            run.stored_filename = filename
            run.content_type = "text/csv; charset=utf-8"
            run.size_bytes = len(content)
            run.sha256 = hashlib.sha256(content).hexdigest()
            run.status = "completed"
        except (AnalyticsReportError, ValueError, OSError) as exc:
            run.status = "failed"
            run.error_message = str(exc)[:1000]
        run.completed_at = current
        runs.append(run)
    db.commit()
    for run in runs:
        db.refresh(run)
    return runs


def report_run_path(run: AnalyticsReportRun, storage_root: str) -> Path:
    if run.status != "completed" or not run.stored_filename:
        raise AnalyticsReportError("Report run has no completed artifact")
    root = Path(storage_root).resolve()
    path = (root / run.stored_filename).resolve()
    if path.parent != root or not path.is_file():
        raise AnalyticsReportError("Report artifact is unavailable")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if run.size_bytes != size or run.sha256 != digest.hexdigest():
        raise AnalyticsReportError("Report artifact failed its integrity check")
    return path
