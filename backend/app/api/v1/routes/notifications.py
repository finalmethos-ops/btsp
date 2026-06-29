from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.notification import (
    NotificationEmitInput,
    NotificationEventResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from app.services.notification_service import (
    NotificationError,
    create_notification_template,
    emit_notification,
    list_notification_events,
    list_notification_templates,
    retry_notification_event,
    seed_bpp_notification_defaults,
    update_notification_template,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/templates", response_model=list[NotificationTemplateResponse])
def read_notification_templates(
    workflow_code: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("notifications.read")),
) -> list[NotificationTemplateResponse]:
    return list_notification_templates(db, workflow_code=workflow_code, event_type=event_type)


@router.post("/templates", response_model=NotificationTemplateResponse)
def write_notification_template(
    payload: NotificationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("notifications.manage")),
) -> NotificationTemplateResponse:
    try:
        return create_notification_template(db, payload, actor=current_user.email)
    except NotificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/templates/{template_code}", response_model=NotificationTemplateResponse)
def patch_notification_template(
    template_code: str,
    payload: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("notifications.manage")),
) -> NotificationTemplateResponse:
    template = update_notification_template(db, template_code, payload, actor=current_user.email)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.get("/events", response_model=list[NotificationEventResponse])
def read_notification_events(
    workflow_code: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("notifications.read")),
) -> list[NotificationEventResponse]:
    return list_notification_events(
        db,
        workflow_code=workflow_code,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )


@router.post("/emit", response_model=list[NotificationEventResponse])
def emit_workflow_notification(
    payload: NotificationEmitInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("notifications.send")),
) -> list[NotificationEventResponse]:
    trusted_payload = payload.model_copy(update={"actor": current_user.email})
    return emit_notification(db, trusted_payload)


@router.post("/events/{notification_id}/retry", response_model=NotificationEventResponse)
def retry_failed_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("notifications.manage")),
) -> NotificationEventResponse:
    try:
        event = retry_notification_event(db, notification_id, current_user.email)
    except NotificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationEventResponse.model_validate(event)


@router.post("/seeds/bpp-purchasing")
def seed_bpp_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow.bpp.notifications.manage")),
) -> dict[str, int]:
    configuration_count, template_count = seed_bpp_notification_defaults(
        db,
        actor=current_user.email,
    )
    return {
        "configuration_entries_seeded": configuration_count,
        "templates_seeded": template_count,
    }
