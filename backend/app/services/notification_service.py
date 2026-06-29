from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role, User
from app.models.notification import NotificationEvent, NotificationTemplate
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.notification import (
    NotificationChannel,
    NotificationEmitInput,
    NotificationStatus,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    RecipientStrategy,
)
from app.services.configuration_service import upsert_config_entry
from app.services.notification_defaults import (
    BPP_NOTIFICATION_CONFIGURATION_DEFAULTS,
    BPP_NOTIFICATION_PERMISSION_DEFINITIONS,
    BPP_NOTIFICATION_TEMPLATES,
    GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS,
)
from app.services.permission_seed_service import seed_permissions_for_roles
from app.services.snapshot_service import append_snapshot


class NotificationError(ValueError):
    pass


class TemplateRenderError(NotificationError):
    pass


def create_notification_template(
    db: Session,
    payload: NotificationTemplateCreate,
    actor: str = "system",
) -> NotificationTemplate:
    existing = db.scalar(
        select(NotificationTemplate).where(
            NotificationTemplate.template_code == payload.template_code
        )
    )
    if existing is not None:
        raise NotificationError("Notification template already exists")
    template = NotificationTemplate(**payload.model_dump(mode="json"))
    db.add(template)
    db.add(
        EventSnapshot(
            event_type="admin.notification_template.created",
            entity_type="notification_template",
            entity_id=template.template_code,
            actor=actor,
            payload={"workflow_code": template.workflow_code, "channel": template.channel},
        )
    )
    db.commit()
    db.refresh(template)
    return template


def update_notification_template(
    db: Session,
    template_code: str,
    payload: NotificationTemplateUpdate,
    actor: str = "system",
) -> NotificationTemplate | None:
    template = db.scalar(
        select(NotificationTemplate).where(NotificationTemplate.template_code == template_code)
    )
    if template is None:
        return None
    updates = payload.model_dump(exclude_unset=True, mode="json")
    candidate = NotificationTemplateCreate(
        template_code=template.template_code,
        workflow_code=updates.get("workflow_code", template.workflow_code),
        event_type=updates.get("event_type", template.event_type),
        channel=updates.get("channel", template.channel),
        subject_template=updates.get("subject_template", template.subject_template),
        body_template=updates.get("body_template", template.body_template),
        recipient_strategy=updates.get("recipient_strategy", template.recipient_strategy),
        recipient_config=updates.get("recipient_config", template.recipient_config),
        is_active=updates.get("is_active", template.is_active),
    )
    for field, value in candidate.model_dump(exclude={"template_code"}, mode="json").items():
        setattr(template, field, value)
    db.add(
        EventSnapshot(
            event_type="admin.notification_template.updated",
            entity_type="notification_template",
            entity_id=template.template_code,
            actor=actor,
            payload={
                "changed_fields": sorted(payload.model_fields_set),
                "is_active": template.is_active,
            },
        )
    )
    db.commit()
    db.refresh(template)
    return template


def list_notification_templates(
    db: Session,
    workflow_code: str | None = None,
    event_type: str | None = None,
) -> list[NotificationTemplate]:
    statement = select(NotificationTemplate)
    if workflow_code is not None:
        statement = statement.where(NotificationTemplate.workflow_code == workflow_code)
    if event_type is not None:
        statement = statement.where(NotificationTemplate.event_type == event_type)
    statement = statement.order_by(NotificationTemplate.template_code)
    return list(db.scalars(statement).all())


def _recipient_values(config: dict[str, Any], key: str) -> list[str]:
    values = config.get(key, [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise NotificationError(f"Recipient configuration must provide a string list: {key}")
    return values


def resolve_recipients(
    db: Session,
    strategy: RecipientStrategy,
    recipient_config: dict[str, Any],
    payload: NotificationEmitInput,
) -> list[str]:
    if strategy == RecipientStrategy.ACTOR:
        return [payload.actor]
    if strategy == RecipientStrategy.STATIC_RECIPIENTS:
        return sorted(set(_recipient_values(recipient_config, "recipients")))
    if strategy == RecipientStrategy.WORKFLOW_ROLE:
        role_codes = _recipient_values(recipient_config, "role_codes")
        statement = (
            select(User.email)
            .join(User.roles)
            .where(Role.code.in_(role_codes), User.is_active.is_(True))
            .distinct()
        )
    elif strategy == RecipientStrategy.PERMISSION_HOLDERS:
        permission_codes = _recipient_values(recipient_config, "permission_codes")
        statement = (
            select(User.email)
            .join(User.roles)
            .join(Role.permissions)
            .where(Permission.code.in_(permission_codes), User.is_active.is_(True))
            .distinct()
        )
    elif strategy == RecipientStrategy.REGION_ADMINS:
        region_code = payload.context.get("region_code")
        if not isinstance(region_code, str):
            return []
        role_codes = _recipient_values(recipient_config, "role_codes") or ["BPP_ADMIN"]
        statement = (
            select(User.email)
            .join(User.roles)
            .where(
                Role.code.in_(role_codes),
                User.region_code == region_code,
                User.is_active.is_(True),
            )
            .distinct()
        )
    elif strategy == RecipientStrategy.STORE_USERS:
        store_number = payload.context.get("store_number")
        if not isinstance(store_number, str):
            return []
        statement = select(User.email).where(
            User.home_store_number == store_number,
            User.is_active.is_(True),
        )
    else:
        raise NotificationError(f"Unsupported recipient strategy: {strategy}")
    return sorted(set(db.scalars(statement).all()))


def render_template(
    template: NotificationTemplate,
    payload: NotificationEmitInput,
) -> tuple[str, str]:
    values = {
        **payload.context,
        "workflow_code": payload.workflow_code,
        "event_type": payload.event_type,
        "entity_type": payload.entity_type,
        "entity_id": payload.entity_id,
        "actor": payload.actor,
    }
    try:
        return template.subject_template.format_map(values), template.body_template.format_map(
            values
        )
    except (KeyError, ValueError) as exc:
        raise TemplateRenderError(f"Unable to render template {template.template_code}") from exc


def _notification_setting(
    db: Session,
    workflow_code: str,
    key: str,
) -> dict[str, Any] | None:
    entry = db.scalar(
        select(ConfigurationEntry).where(
            ConfigurationEntry.scope_type == "workflow",
            ConfigurationEntry.scope_key == workflow_code,
            ConfigurationEntry.key == key,
            ConfigurationEntry.is_active.is_(True),
        )
    )
    return None if entry is None else entry.value


def _channel_status(
    db: Session,
    workflow_code: str,
    channel: NotificationChannel,
) -> NotificationStatus:
    enabled = _notification_setting(db, workflow_code, "notification.enabled")
    if enabled is not None and enabled.get("enabled") is False:
        return NotificationStatus.SKIPPED
    channels = _notification_setting(db, workflow_code, "notification.channels")
    if channels is not None and channel not in channels.get("channels", []):
        return NotificationStatus.SKIPPED
    if channel == NotificationChannel.WEBHOOK:
        webhook = _notification_setting(db, workflow_code, "notification.webhook_enabled")
        if webhook is None or webhook.get("enabled") is not True:
            return NotificationStatus.SKIPPED
    return NotificationStatus.QUEUED


def _record_notification_snapshot(
    db: Session,
    event: NotificationEvent,
    snapshot_event_type: str,
) -> None:
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type=snapshot_event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            actor=event.actor,
            payload={
                "workflow_code": event.workflow_code,
                "event_type": event.event_type,
                "template_code": event.template_code,
                "channel": event.channel,
                "recipient_strategy": event.recipient_strategy,
                "status": event.status,
            },
        ),
    )


def emit_notification(
    db: Session,
    payload: NotificationEmitInput,
) -> list[NotificationEvent]:
    templates = db.scalars(
        select(NotificationTemplate)
        .where(
            NotificationTemplate.workflow_code == payload.workflow_code,
            NotificationTemplate.event_type == payload.event_type,
        )
        .order_by(NotificationTemplate.template_code)
    ).all()
    events: list[NotificationEvent] = []
    for template in templates:
        status = NotificationStatus.SKIPPED
        recipients: list[str] = []
        subject = ""
        body = ""
        error_message = None
        try:
            if template.is_active:
                strategy = RecipientStrategy(template.recipient_strategy)
                channel = NotificationChannel(template.channel)
                recipients = resolve_recipients(db, strategy, template.recipient_config, payload)
                subject, body = render_template(template, payload)
                status = _channel_status(db, payload.workflow_code, channel)
        except (NotificationError, ValueError) as exc:
            status = NotificationStatus.FAILED
            error_message = str(exc)

        event = NotificationEvent(
            template_code=template.template_code,
            workflow_code=payload.workflow_code,
            event_type=payload.event_type,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            actor=payload.actor,
            channel=template.channel,
            recipient_strategy=template.recipient_strategy,
            resolved_recipients=recipients,
            subject=subject,
            body=body,
            status=status,
            error_message=error_message,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        _record_notification_snapshot(
            db,
            event,
            "notification.failed"
            if status == NotificationStatus.FAILED
            else "notification.emitted",
        )
        events.append(event)
    return events


def list_notification_events(
    db: Session,
    workflow_code: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 100,
) -> list[NotificationEvent]:
    statement = select(NotificationEvent)
    if workflow_code is not None:
        statement = statement.where(NotificationEvent.workflow_code == workflow_code)
    if entity_type is not None:
        statement = statement.where(NotificationEvent.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(NotificationEvent.entity_id == entity_id)
    statement = statement.order_by(NotificationEvent.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def mark_notification_sent(db: Session, notification_id: int) -> NotificationEvent | None:
    event = db.get(NotificationEvent, notification_id)
    if event is None:
        return None
    event.status = NotificationStatus.SENT
    event.error_message = None
    event.sent_at = datetime.now(UTC)
    db.commit()
    db.refresh(event)
    return event


def mark_notification_failed(
    db: Session,
    notification_id: int,
    error_message: str,
) -> NotificationEvent | None:
    event = db.get(NotificationEvent, notification_id)
    if event is None:
        return None
    event.status = NotificationStatus.FAILED
    event.error_message = error_message
    db.commit()
    db.refresh(event)
    _record_notification_snapshot(db, event, "notification.failed")
    return event


def retry_notification_event(
    db: Session, notification_id: int, actor: str
) -> NotificationEvent | None:
    event = db.get(NotificationEvent, notification_id)
    if event is None:
        return None
    if event.status != NotificationStatus.FAILED:
        raise NotificationError("Only failed notification deliveries can be requeued")
    if not event.subject or not event.body or not event.resolved_recipients:
        raise NotificationError("Notification must be rendered with recipients before retry")
    event.status = NotificationStatus.QUEUED
    event.error_message = None
    event.sent_at = None
    db.add(
        EventSnapshot(
            event_type="admin.notification.requeued",
            entity_type="notification_event",
            entity_id=str(event.id),
            actor=actor,
            payload={
                "template_code": event.template_code,
                "workflow_code": event.workflow_code,
                "original_actor": event.actor,
            },
        )
    )
    db.commit()
    db.refresh(event)
    return event


def _seed_notification_permissions(db: Session) -> None:
    definitions = {
        **GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS,
        **BPP_NOTIFICATION_PERMISSION_DEFINITIONS,
    }
    seed_permissions_for_roles(
        db,
        definitions,
        {
            "SYSTEM_ADMIN": set(definitions),
            "BPP_ADMIN": {
                "notifications.read",
                "notifications.send",
                "workflow.bpp.notifications.manage",
            },
        },
    )


def seed_bpp_notification_defaults(db: Session, actor: str) -> tuple[int, int]:
    _seed_notification_permissions(db)
    for default in BPP_NOTIFICATION_CONFIGURATION_DEFAULTS:
        upsert_config_entry(
            db,
            default.model_copy(deep=True, update={"updated_by": actor}),
        )
    for default in BPP_NOTIFICATION_TEMPLATES:
        existing = db.scalar(
            select(NotificationTemplate).where(
                NotificationTemplate.template_code == default.template_code
            )
        )
        if existing is None:
            create_notification_template(db, default.model_copy(deep=True), actor=actor)
        else:
            update_notification_template(
                db,
                default.template_code,
                NotificationTemplateUpdate(**default.model_dump(exclude={"template_code"})),
                actor=actor,
            )
    return len(BPP_NOTIFICATION_CONFIGURATION_DEFAULTS), len(BPP_NOTIFICATION_TEMPLATES)
