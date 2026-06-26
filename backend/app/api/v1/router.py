from fastapi import APIRouter

from app.api.v1.routes import auth, health, snapshots, stores, system, workflows

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(workflows.router)
api_router.include_router(stores.router)
api_router.include_router(snapshots.router)
