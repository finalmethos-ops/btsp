from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter()


@router.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def read_ready() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("select 1"))

    redis_client = Redis.from_url(settings.redis_url)
    redis_client.ping()

    return {"status": "ready"}
