import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.background_automation import event_task_reminder_loop

access_logger = logging.getLogger("btsp.access")
access_logger.setLevel(logging.INFO)
if not access_logger.handlers:
    access_handler = logging.StreamHandler()
    access_handler.setFormatter(logging.Formatter("%(message)s"))
    access_logger.addHandler(access_handler)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def request_id_from_header(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex


@asynccontextmanager
async def lifespan(_app: FastAPI):
    reminder_task = asyncio.create_task(event_task_reminder_loop())
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-BTSP-Bootstrap-Token",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        request_id = request_id_from_header(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            for header, value in SECURITY_HEADERS.items():
                response.headers.setdefault(header, value)
            if request.url.path.startswith("/api/"):
                response.headers.setdefault("Cache-Control", "no-store")
            return response
        finally:
            access_logger.info(
                json.dumps(
                    {
                        "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
                        "event": "http_request",
                        "method": request.method,
                        "path": request.url.path,
                        "request_id": request_id,
                        "status": status_code,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
