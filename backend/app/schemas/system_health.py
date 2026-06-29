from datetime import datetime
from typing import Literal

from pydantic import BaseModel

HealthStatus = Literal["healthy", "degraded", "unavailable"]


class DependencyHealth(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: float | None
    detail: str | None = None


class StorageHealth(BaseModel):
    name: str
    status: HealthStatus
    writable: bool
    free_bytes: int | None


class OperationalHealthMetric(BaseModel):
    name: str
    count: int
    severity: Literal["info", "warning"]


class SystemDiagnosticsResponse(BaseModel):
    status: HealthStatus
    application: str
    version: str
    environment: str
    database_revision: str | None
    uptime_seconds: int
    generated_at: datetime
    dependencies: list[DependencyHealth]
    storage: list[StorageHealth]
    operational_metrics: list[OperationalHealthMetric]
