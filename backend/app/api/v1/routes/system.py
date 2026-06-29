from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.core.config import settings
from app.db.session import engine, get_db
from app.models.identity import User
from app.schemas.system_health import SystemDiagnosticsResponse
from app.services.system_health_service import system_diagnostics

router = APIRouter()


@router.get("/version")
def read_version() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/diagnostics", response_model=SystemDiagnosticsResponse)
def read_system_diagnostics(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("system.health.read")),
) -> SystemDiagnosticsResponse:
    return system_diagnostics(db, engine, settings)
