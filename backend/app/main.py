import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.background_automation import event_task_reminder_loop

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


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
        allow_headers=["Authorization", "Content-Type", "X-BTSP-Bootstrap-Token"],
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
