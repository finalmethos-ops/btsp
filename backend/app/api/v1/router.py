from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    analytics,
    approval_policies,
    audit,
    auth,
    bootstrap,
    catalog,
    communications,
    configuration,
    event_announcements,
    event_attendance,
    event_buy_fair,
    event_calendar,
    event_closeout_insights,
    event_feedback,
    event_live_insights,
    event_management,
    event_order_review,
    event_ordering,
    event_polls,
    event_presentations,
    event_product_slides,
    event_realtime,
    event_settlement,
    event_staff_tasks,
    event_summary,
    event_vendor_booths,
    health,
    inventory,
    invoice_intake,
    invoices,
    model_catalog,
    notifications,
    order_lifecycle,
    purchase_orders,
    purchase_requests,
    receiving,
    reconciliation,
    roles,
    store_loadout,
    stores,
    system,
    users,
    vendor_hall,
    vendor_integrations,
    vendor_models,
    vendor_profile,
    vendor_reports,
    workflow_admin,
    workflow_engine,
    workflow_registry,
    workflows,
)
from app.auth.event_scope import (
    enforce_event_login_scope,
    enforce_event_portal_api_boundary,
)

api_router = APIRouter(dependencies=[Depends(enforce_event_portal_api_boundary)])
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(invoices.router)
api_router.include_router(invoice_intake.router)
api_router.include_router(inventory.router)
api_router.include_router(model_catalog.router)
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(approval_policies.router)
api_router.include_router(notifications.router)
api_router.include_router(order_lifecycle.router)
api_router.include_router(purchase_requests.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(receiving.router)
api_router.include_router(reconciliation.router)
api_router.include_router(roles.router)
event_scope_dependencies = [Depends(enforce_event_login_scope)]

api_router.include_router(store_loadout.router, dependencies=event_scope_dependencies)
api_router.include_router(workflows.router)
api_router.include_router(stores.router)
api_router.include_router(configuration.router)
api_router.include_router(event_management.router, dependencies=event_scope_dependencies)
api_router.include_router(event_attendance.router, dependencies=event_scope_dependencies)
api_router.include_router(event_buy_fair.router, dependencies=event_scope_dependencies)
api_router.include_router(event_announcements.router, dependencies=event_scope_dependencies)
api_router.include_router(event_calendar.router, dependencies=event_scope_dependencies)
api_router.include_router(event_closeout_insights.router, dependencies=event_scope_dependencies)
api_router.include_router(event_feedback.router, dependencies=event_scope_dependencies)
api_router.include_router(event_ordering.router, dependencies=event_scope_dependencies)
api_router.include_router(event_polls.router, dependencies=event_scope_dependencies)
api_router.include_router(event_order_review.router, dependencies=event_scope_dependencies)
api_router.include_router(event_product_slides.router, dependencies=event_scope_dependencies)
api_router.include_router(event_realtime.router)
api_router.include_router(event_settlement.router, dependencies=event_scope_dependencies)
api_router.include_router(event_summary.router, dependencies=event_scope_dependencies)
api_router.include_router(event_presentations.router, dependencies=event_scope_dependencies)
api_router.include_router(event_presentations.public_router)
api_router.include_router(event_staff_tasks.router, dependencies=event_scope_dependencies)
api_router.include_router(event_vendor_booths.router, dependencies=event_scope_dependencies)
api_router.include_router(event_live_insights.router, dependencies=event_scope_dependencies)
api_router.include_router(communications.router)
api_router.include_router(bootstrap.router)
api_router.include_router(users.router)
api_router.include_router(vendor_integrations.router)
api_router.include_router(vendor_hall.router, dependencies=event_scope_dependencies)
api_router.include_router(vendor_models.router)
api_router.include_router(vendor_profile.router)
api_router.include_router(vendor_reports.router)
api_router.include_router(workflow_engine.router)
api_router.include_router(workflow_admin.router)
api_router.include_router(workflow_registry.router)
