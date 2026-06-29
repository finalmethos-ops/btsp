from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.db.session import engine
from app.services.system_health_service import dependencies_ready

router = APIRouter()


@router.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def read_ready(response: Response) -> dict[str, str]:
    if not dependencies_ready(engine, settings.redis_url):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}
    return {"status": "ready"}
