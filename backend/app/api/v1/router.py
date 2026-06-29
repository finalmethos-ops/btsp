from fastapi import APIRouter

from app.api.v1.routes import (
    analytics,
    approval_policies,
    audit,
    auth,
    bootstrap,
    catalog,
    configuration,
    health,
    invoices,
    notifications,
    purchase_orders,
    purchase_requests,
    receiving,
    reconciliation,
    roles,
    snapshots,
    stores,
    system,
    users,
    vendor_integrations,
    workflow_admin,
    workflow_engine,
    workflow_registry,
    workflows,
)

api_router = APIRouter()
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(invoices.router)
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(approval_policies.router)
api_router.include_router(notifications.router)
api_router.include_router(purchase_requests.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(receiving.router)
api_router.include_router(reconciliation.router)
api_router.include_router(roles.router)
api_router.include_router(workflows.router)
api_router.include_router(stores.router)
api_router.include_router(snapshots.router)
api_router.include_router(configuration.router)
api_router.include_router(bootstrap.router)
api_router.include_router(users.router)
api_router.include_router(vendor_integrations.router)
api_router.include_router(workflow_engine.router)
api_router.include_router(workflow_admin.router)
api_router.include_router(workflow_registry.router)
