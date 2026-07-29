import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.auth.dependencies import get_current_user, get_login_context
from app.auth.security import decode_access_token
from app.db.session import get_db
from app.models.event_management import (
    EventEntityOrder,
    EventPoll,
    EventProductSlide,
    EventSettlementException,
    EventStaffTask,
    EventVendorBooth,
    ManagedSubEvent,
    StoreLoadoutAssignment,
    VendorHallBooth,
)
from app.models.identity import User
from app.services.event_access_service import active_event_membership

EVENT_SCOPE_COLLECTION_ROUTES = frozenset(
    {
        "/api/v1/events/mine",
        "/api/v1/events/modules",
        "/api/v1/events/account-directory",
        "/api/v1/event-attendance/mine",
        "/api/v1/event-announcements/mine",
        "/api/v1/event-calendar/mine",
        "/api/v1/event-ordering/assignments",
        "/api/v1/event-product-slides/web-fill",
        "/api/v1/event-staff-tasks/mine",
        "/api/v1/event-vendor-booths/mine",
        "/api/v1/store-loadout/mine",
        "/api/v1/vendor-hall/mine",
    }
)

EVENT_PORTAL_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/event-",
    "/api/v1/events/",
    "/api/v1/store-loadout/",
    "/api/v1/vendor-hall/",
)


def enforce_event_portal_api_boundary(connection: HTTPConnection) -> None:
    """Keep event-context bearer tokens inside event portal APIs."""
    scheme, token = get_authorization_scheme_param(connection.headers.get("Authorization"))
    if scheme.lower() != "bearer" or not token:
        return
    try:
        login_context = decode_access_token(token).get("login_context", "standard")
    except jwt.PyJWTError:
        # Authentication dependencies remain responsible for invalid-token responses.
        return
    if login_context != "event":
        return

    path = connection.url.path.rstrip("/")
    method = connection.scope.get("method", "GET")
    if path.startswith(EVENT_PORTAL_PREFIXES):
        return
    if path in {"/api/v1/events", "/api/v1/auth/me"}:
        return
    if path.startswith("/api/v1/communications/"):
        return
    if method == "GET" and (
        path == "/api/v1/model-catalog"
        or path.startswith("/api/v1/model-catalog/")
        or path == "/api/v1/stores/management"
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Event-login sessions cannot access standard platform operations",
    )


def _event_id_from_request(db: Session, request: Request) -> str | None:
    params = request.path_params
    event_id = params.get("event_id")
    if event_id:
        return event_id

    resource_lookups = (
        ("sub_event_id", ManagedSubEvent),
        ("poll_id", EventPoll),
        ("slide_id", EventProductSlide),
        ("task_id", EventStaffTask),
        ("order_id", EventEntityOrder),
        ("exception_id", EventSettlementException),
        ("assignment_id", StoreLoadoutAssignment),
    )
    for parameter, model in resource_lookups:
        resource_id = params.get(parameter)
        if resource_id:
            resource = db.get(model, resource_id)
            return resource.event_id if resource is not None else None

    booth_id = params.get("booth_id")
    if booth_id:
        booth = db.get(VendorHallBooth, booth_id) or db.get(EventVendorBooth, booth_id)
        return booth.event_id if booth is not None else None
    return None


def enforce_event_login_scope(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
) -> None:
    if login_context != "event":
        return
    path = request.url.path.rstrip("/")
    if path in EVENT_SCOPE_COLLECTION_ROUTES:
        return
    event_id = _event_id_from_request(db, request)
    if event_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Event-login sessions are limited to registered event resources",
        )
    if active_event_membership(db, event_id, user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not registered for the requested event",
        )
