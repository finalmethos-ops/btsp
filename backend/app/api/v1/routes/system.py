from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/version")
def read_version() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
