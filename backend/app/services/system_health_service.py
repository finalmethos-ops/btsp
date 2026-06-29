import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from redis import Redis
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.analytics import AnalyticsReportRun
from app.models.notification import NotificationEvent
from app.models.vendor_integration import VendorConnectorImportRun
from app.schemas.system_health import (
    DependencyHealth,
    OperationalHealthMetric,
    StorageHealth,
    SystemDiagnosticsResponse,
)

PROCESS_STARTED_AT = time.monotonic()


def _database_health(engine: Engine) -> DependencyHealth:
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        latency = round((time.perf_counter() - started) * 1000, 2)
        return DependencyHealth(name="database", status="healthy", latency_ms=latency)
    except Exception as exc:  # Dependency drivers expose unrelated exception hierarchies.
        return DependencyHealth(
            name="database",
            status="unavailable",
            latency_ms=None,
            detail=type(exc).__name__,
        )


def _redis_health(redis_url: str) -> DependencyHealth:
    started = time.perf_counter()
    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        latency = round((time.perf_counter() - started) * 1000, 2)
        return DependencyHealth(name="redis", status="healthy", latency_ms=latency)
    except Exception as exc:  # Dependency drivers expose unrelated exception hierarchies.
        return DependencyHealth(
            name="redis",
            status="unavailable",
            latency_ms=None,
            detail=type(exc).__name__,
        )


def _storage_health(name: str, raw_path: str) -> StorageHealth:
    path = Path(raw_path)
    try:
        writable = path.is_dir() and os.access(path, os.W_OK)
        free_bytes = shutil.disk_usage(path).free if path.exists() else None
    except OSError:
        writable = False
        free_bytes = None
    return StorageHealth(
        name=name,
        status="healthy" if writable else "unavailable",
        writable=writable,
        free_bytes=free_bytes,
    )


def dependencies_ready(engine: Engine, redis_url: str) -> bool:
    checks = [_database_health(engine), _redis_health(redis_url)]
    return all(item.status == "healthy" for item in checks)


def _failed_count(db: Session, model: type, statuses: tuple[str, ...]) -> int:
    return int(
        db.scalar(select(func.count()).select_from(model).where(model.status.in_(statuses))) or 0
    )


def system_diagnostics(
    db: Session, engine: Engine, settings: Settings
) -> SystemDiagnosticsResponse:
    dependencies = [_database_health(engine), _redis_health(settings.redis_url)]
    storage = [
        _storage_health("attachments", settings.attachment_storage_path),
        _storage_health("purchase_order_exports", settings.purchase_order_export_path),
        _storage_health("analytics_reports", settings.analytics_report_path),
    ]
    metrics: list[OperationalHealthMetric] = []
    database_revision = None
    if dependencies[0].status == "healthy":
        try:
            database_revision = db.execute(text("select version_num from alembic_version")).scalar()
            values = [
                ("failed_notifications", _failed_count(db, NotificationEvent, ("failed",))),
                ("failed_analytics_reports", _failed_count(db, AnalyticsReportRun, ("failed",))),
                (
                    "failed_connector_imports",
                    _failed_count(db, VendorConnectorImportRun, ("failed", "dead_letter")),
                ),
            ]
            metrics = [
                OperationalHealthMetric(
                    name=name,
                    count=count,
                    severity="warning" if count else "info",
                )
                for name, count in values
            ]
        except Exception:
            db.rollback()
            dependencies[0].status = "degraded"
            dependencies[0].detail = "DiagnosticsQueryError"
    unavailable = any(item.status == "unavailable" for item in [*dependencies, *storage])
    degraded = any(item.status == "degraded" for item in dependencies) or any(
        item.severity == "warning" for item in metrics
    )
    return SystemDiagnosticsResponse(
        status="unavailable" if unavailable else "degraded" if degraded else "healthy",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database_revision=database_revision,
        uptime_seconds=max(0, int(time.monotonic() - PROCESS_STARTED_AT)),
        generated_at=datetime.now(UTC),
        dependencies=dependencies,
        storage=storage,
        operational_metrics=metrics,
    )
