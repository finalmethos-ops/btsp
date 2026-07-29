from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.permissions import user_has_permission
from app.models.event_management import (
    EventMembership,
    EventStaffTask,
    EventStaffTaskAttachment,
    ManagedEvent,
    ManagedSubEvent,
    VendorHallBooth,
)
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Role, User
from app.models.notification import NotificationEvent, UserNotificationPreference
from app.schemas.event_staff_task import (
    EventStaffTaskAttachmentResponse,
    EventStaffTaskResponse,
    EventStaffTaskStatusWrite,
    EventStaffTaskWrite,
)
from app.services.event_access_service import (
    active_event_membership,
    event_operations_are_locked,
    membership_has_sub_event_access,
)
from app.services.upload_validation import content_matches_declared_type


class EventStaffTaskError(ValueError):
    pass


class EventStaffTaskAccessError(PermissionError):
    pass


MAX_TASK_EVIDENCE_BYTES = 8 * 1024 * 1024
TASK_EVIDENCE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
STAFF_TASK_MEMBERSHIP_TYPES = {
    "staff",
    "admin",
    "team_lead",
    "dockmaster",
    "overseer",
}


def _task_action_href(task: EventStaffTask) -> str:
    if task.sub_event_id:
        return f"/events/sub-event/{task.sub_event_id}"
    return f"/events/calendar?event_id={task.event_id}"


def _audit_payload(task: EventStaffTask) -> dict:
    return {
        "event_id": task.event_id,
        "sub_event_id": task.sub_event_id,
        "assigned_membership_id": task.assigned_membership_id,
        "vendor_hall_booth_id": task.vendor_hall_booth_id,
        "title": task.title,
        "priority": task.priority,
        "status": task.status,
        "status_note": task.status_note,
        "task_phase": task.task_phase,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "completed_by": task.completed_by,
    }


def _event_admin_emails(db: Session, event_id: str) -> list[str]:
    event_admins = db.scalars(
        select(User)
        .join(EventMembership, EventMembership.user_id == User.id)
        .where(
            EventMembership.event_id == event_id,
            EventMembership.is_active.is_(True),
            EventMembership.membership_type == "admin",
            User.is_active.is_(True),
        )
    ).all()
    platform_admins = db.scalars(
        select(User)
        .join(User.roles)
        .where(User.is_active.is_(True), Role.code.in_(("SYSTEM_ADMIN", "ADMIN")))
    ).all()
    return sorted({user.email for user in [*event_admins, *platform_admins]})


def _in_quiet_hours(preference: UserNotificationPreference | None, now: datetime) -> bool:
    if preference is None or not preference.quiet_hours_start or not preference.quiet_hours_end:
        return False
    current = now.hour * 60 + now.minute
    start_hour, start_minute = map(int, preference.quiet_hours_start.split(":"))
    end_hour, end_minute = map(int, preference.quiet_hours_end.split(":"))
    start = start_hour * 60 + start_minute
    end = end_hour * 60 + end_minute
    return current >= start and current < end if start <= end else current >= start or current < end


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _response(db: Session, task: EventStaffTask) -> EventStaffTaskResponse:
    event = db.get(ManagedEvent, task.event_id)
    membership = db.get(EventMembership, task.assigned_membership_id)
    assignee = db.get(User, membership.user_id) if membership else None
    sub_event = db.get(ManagedSubEvent, task.sub_event_id) if task.sub_event_id else None
    booth = (
        db.get(VendorHallBooth, task.vendor_hall_booth_id) if task.vendor_hall_booth_id else None
    )
    attachments = db.scalars(
        select(EventStaffTaskAttachment)
        .where(EventStaffTaskAttachment.task_id == task.id)
        .order_by(EventStaffTaskAttachment.created_at, EventStaffTaskAttachment.filename)
    ).all()
    return EventStaffTaskResponse(
        id=task.id,
        event_id=task.event_id,
        event_name=event.name if event else "Event",
        sub_event_id=task.sub_event_id,
        vendor_hall_booth_id=task.vendor_hall_booth_id,
        sub_event_name=sub_event.name if sub_event else None,
        vendor_hall_booth_name=booth.booth_name if booth else None,
        assigned_membership_id=task.assigned_membership_id,
        assigned_display_name=assignee.display_name if assignee else "Assigned staff",
        assigned_email=assignee.email if assignee else "",
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        status_note=task.status_note,
        due_at=task.due_at,
        completed_at=task.completed_at,
        completed_by=task.completed_by,
        attachments=[
            EventStaffTaskAttachmentResponse(
                id=attachment.id,
                task_id=attachment.task_id,
                filename=attachment.filename,
                content_type=attachment.content_type,
                uploaded_by=attachment.uploaded_by,
                created_at=attachment.created_at,
            )
            for attachment in attachments
        ],
        updated_at=task.updated_at,
    )


def _task_access_allowed(db: Session, task: EventStaffTask, user: User) -> bool:
    membership = active_event_membership(db, task.event_id, user.id)
    return bool(
        membership
        and (membership.id == task.assigned_membership_id or membership.membership_type == "admin")
        or user_has_permission(user, "events.manage")
    )


def attach_task_evidence(
    db: Session,
    task_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    user: User,
) -> EventStaffTaskAttachmentResponse | None:
    task = db.get(EventStaffTask, task_id)
    if task is None:
        return None
    if event_operations_are_locked(db, task.event_id):
        raise EventStaffTaskError(
            "Task evidence is locked because the event is cancelled or settlement is closed"
        )
    if not _task_access_allowed(db, task, user):
        raise EventStaffTaskAccessError("Task is outside this user's event assignment")
    if task.status == "cancelled":
        raise EventStaffTaskError("Evidence cannot be added to a cancelled task")
    if content_type not in TASK_EVIDENCE_CONTENT_TYPES:
        raise EventStaffTaskError("Task evidence must be JPEG, PNG, or WebP")
    if not content or len(content) > MAX_TASK_EVIDENCE_BYTES:
        raise EventStaffTaskError("Task evidence must be between 1 byte and 8 MB")
    if not content_matches_declared_type(content, content_type):
        raise EventStaffTaskError("Task evidence content does not match its declared type")
    attachment_count = db.scalar(
        select(func.count(EventStaffTaskAttachment.id)).where(
            EventStaffTaskAttachment.task_id == task.id
        )
    )
    if (attachment_count or 0) >= 5:
        raise EventStaffTaskError("A task can have no more than 5 evidence photos")
    safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip() or "evidence"
    attachment = EventStaffTaskAttachment(
        task_id=task.id,
        event_id=task.event_id,
        filename=safe_filename[:255],
        content_type=content_type,
        content=content,
        uploaded_by=user.email,
    )
    db.add(attachment)
    db.flush()
    db.add(
        EventSnapshot(
            event_type="event_staff_task.evidence_uploaded",
            entity_type="event_staff_task",
            entity_id=task.id,
            actor=user.email,
            payload={
                "event_id": task.event_id,
                "attachment_id": attachment.id,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "size_bytes": len(content),
            },
        )
    )
    db.commit()
    db.refresh(attachment)
    return EventStaffTaskAttachmentResponse(
        id=attachment.id,
        task_id=attachment.task_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        uploaded_by=attachment.uploaded_by,
        created_at=attachment.created_at,
    )


def task_evidence_content(
    db: Session,
    task_id: str,
    attachment_id: str,
    user: User,
) -> tuple[str, str, bytes] | None:
    task = db.get(EventStaffTask, task_id)
    if task is None or not _task_access_allowed(db, task, user):
        return None
    attachment = db.get(EventStaffTaskAttachment, attachment_id)
    if attachment is None or attachment.task_id != task.id:
        return None
    return attachment.filename, attachment.content_type, attachment.content


def _validate_assignment(db: Session, event_id: str, payload: EventStaffTaskWrite) -> None:
    membership = db.get(EventMembership, payload.assigned_membership_id)
    if (
        membership is None
        or membership.event_id != event_id
        or not membership.is_active
        or (
            membership.membership_type not in STAFF_TASK_MEMBERSHIP_TYPES
            and membership.loadout_role is None
        )
    ):
        raise EventStaffTaskError(
            "Task must be assigned to active event staff or event operations personnel"
        )
    if payload.sub_event_id:
        sub_event = db.get(ManagedSubEvent, payload.sub_event_id)
        if sub_event is None or sub_event.event_id != event_id:
            raise EventStaffTaskError("Sub-event does not belong to this event")
        if not membership_has_sub_event_access(db, membership, payload.sub_event_id):
            raise EventStaffTaskError(
                "Assigned staff member does not have access to this sub-event"
            )
    if payload.vendor_hall_booth_id:
        booth = db.get(VendorHallBooth, payload.vendor_hall_booth_id)
        if booth is None or booth.event_id != event_id:
            raise EventStaffTaskError("Vendor hall booth does not belong to this event")


def list_event_tasks(db: Session, event_id: str) -> list[EventStaffTaskResponse] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    tasks = db.scalars(
        select(EventStaffTask)
        .where(EventStaffTask.event_id == event_id)
        .order_by(EventStaffTask.status, EventStaffTask.due_at, EventStaffTask.created_at.desc())
    ).all()
    return [_response(db, task) for task in tasks]


def save_event_task(
    db: Session,
    event_id: str,
    payload: EventStaffTaskWrite,
    actor: str,
    task_id: str | None = None,
) -> EventStaffTaskResponse | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventStaffTaskError(
            "Event staff tasks are locked because the event is cancelled or settlement is closed"
        )
    _validate_assignment(db, event_id, payload)
    task = db.get(EventStaffTask, task_id) if task_id else None
    if task_id and (task is None or task.event_id != event_id):
        return None
    before = _audit_payload(task) if task else None
    if task is None:
        task = EventStaffTask(event_id=event_id, created_by=actor)
        db.add(task)
    for field, value in payload.model_dump().items():
        setattr(task, field, value)
    if payload.status == "done" and (before is None or before["status"] != "done"):
        task.completed_at = datetime.now(UTC)
        task.completed_by = actor
    elif payload.status != "done" and before is not None and before["status"] == "done":
        task.completed_at = None
        task.completed_by = None
    db.flush()
    after = _audit_payload(task)
    transition_to_cancelled = (
        before is not None and before["status"] != "cancelled" and after["status"] == "cancelled"
    )
    db.add(
        EventSnapshot(
            event_type=(
                "event_staff_task.cancelled"
                if transition_to_cancelled
                else "event_staff_task.updated"
                if before
                else "event_staff_task.created"
            ),
            entity_type="event_staff_task",
            entity_id=task.id,
            actor=actor,
            payload={"before": before, "after": after},
        )
    )
    if transition_to_cancelled:
        membership = db.get(EventMembership, task.assigned_membership_id)
        assignee = db.get(User, membership.user_id) if membership else None
        db.add(
            NotificationEvent(
                template_code="EVENT_STAFF_TASK_CANCELLED",
                workflow_code="EVENTS",
                event_type="event_staff_task.cancelled",
                entity_type="event_staff_task",
                entity_id=task.id,
                actor=actor,
                channel="in_app",
                recipient_strategy="static_recipients",
                resolved_recipients=[assignee.email] if assignee else [],
                subject=f"Staff task cancelled: {task.title}",
                body=f"The event staff task '{task.title}' has been cancelled.",
                action_href=_task_action_href(task),
                status="queued",
            )
        )
    db.commit()
    db.refresh(task)
    return _response(db, task)


def update_task_status(
    db: Session, task_id: str, payload: EventStaffTaskStatusWrite, user: User, admin: bool = False
) -> EventStaffTaskResponse | None:
    task = db.get(EventStaffTask, task_id)
    if task is None:
        return None
    if event_operations_are_locked(db, task.event_id):
        raise EventStaffTaskError(
            "Event staff tasks are locked because the event is cancelled or settlement is closed"
        )
    membership = active_event_membership(db, task.event_id, user.id)
    if not admin and (membership is None or membership.id != task.assigned_membership_id):
        raise EventStaffTaskError("Task is not assigned to this user")
    previous_status = task.status
    allowed_staff_transitions = {
        "open": {"in_progress"},
        "blocked": {"in_progress"},
        "in_progress": {"done", "blocked"},
        "done": set(),
        "cancelled": set(),
    }
    if not admin and payload.status not in allowed_staff_transitions.get(previous_status, set()):
        raise EventStaffTaskError(f"Task cannot move from {previous_status} to {payload.status}")
    task.status = payload.status
    task.status_note = payload.note.strip() if payload.note and payload.note.strip() else None
    if payload.status == "done":
        task.completed_at = datetime.now(UTC)
        task.completed_by = user.email
    else:
        task.completed_at = None
        task.completed_by = None
    if payload.status == "done" and previous_status != "done":
        db.add(
            NotificationEvent(
                template_code="EVENT_STAFF_TASK_COMPLETED",
                workflow_code="EVENTS",
                event_type="event_staff_task.completed",
                entity_type="event_staff_task",
                entity_id=task.id,
                actor=user.email,
                channel="in_app",
                recipient_strategy="static_recipients",
                resolved_recipients=_event_admin_emails(db, task.event_id),
                subject=f"Staff task completed: {task.title}",
                body=(
                    f"{user.display_name} completed the event staff task '{task.title}'."
                    + (f" Notes: {task.status_note}" if task.status_note else "")
                ),
                action_href=_task_action_href(task),
                status="queued",
            )
        )
    elif payload.status == "blocked" and previous_status != "blocked":
        db.add(
            NotificationEvent(
                template_code="EVENT_STAFF_TASK_BLOCKED",
                workflow_code="EVENTS",
                event_type="event_staff_task.blocked",
                entity_type="event_staff_task",
                entity_id=task.id,
                actor=user.email,
                channel="in_app",
                recipient_strategy="static_recipients",
                resolved_recipients=_event_admin_emails(db, task.event_id),
                subject=f"Staff task blocked: {task.title}",
                body=(
                    f"{user.display_name} marked the event staff task '{task.title}' blocked."
                    + (f" Notes: {task.status_note}" if task.status_note else "")
                ),
                action_href=_task_action_href(task),
                status="queued",
            )
        )
    db.add(
        EventSnapshot(
            event_type="event_staff_task.status_changed",
            entity_type="event_staff_task",
            entity_id=task.id,
            actor=user.email,
            payload={
                "event_id": task.event_id,
                "sub_event_id": task.sub_event_id,
                "previous_status": previous_status,
                "status": task.status,
                "status_note": task.status_note,
                "completed_at": (task.completed_at.isoformat() if task.completed_at else None),
            },
        )
    )
    db.commit()
    db.refresh(task)
    return _response(db, task)


def my_tasks(db: Session, user: User) -> list[EventStaffTaskResponse]:
    memberships = db.scalars(
        select(EventMembership).where(
            EventMembership.user_id == user.id,
            EventMembership.is_active.is_(True),
            (
                EventMembership.membership_type.in_(STAFF_TASK_MEMBERSHIP_TYPES)
                | EventMembership.loadout_role.is_not(None)
            ),
        )
    ).all()
    if not memberships:
        return []
    tasks = db.scalars(
        select(EventStaffTask)
        .join(ManagedEvent, ManagedEvent.id == EventStaffTask.event_id)
        .where(
            EventStaffTask.assigned_membership_id.in_([item.id for item in memberships]),
            ManagedEvent.status.in_(("draft", "published")),
        )
        .order_by(EventStaffTask.status, EventStaffTask.due_at, EventStaffTask.created_at.desc())
    ).all()
    return [_response(db, task) for task in tasks]


def enqueue_due_task_reminders(
    db: Session,
    now: datetime | None = None,
) -> int:
    current = now or datetime.now(UTC)
    tasks = db.scalars(
        select(EventStaffTask)
        .join(ManagedEvent, ManagedEvent.id == EventStaffTask.event_id)
        .where(
            EventStaffTask.status.in_(("open", "in_progress", "blocked")),
            EventStaffTask.due_at.is_not(None),
            EventStaffTask.due_at <= current + timedelta(hours=24),
            ManagedEvent.status.in_(("draft", "published")),
        )
        .with_for_update(skip_locked=True)
    ).all()
    created = 0
    for task in tasks:
        due_at = _as_utc(task.due_at)
        recent = db.scalar(
            select(NotificationEvent.id).where(
                NotificationEvent.entity_type == "event_staff_task",
                NotificationEvent.entity_id == task.id,
                NotificationEvent.event_type == "event_staff_task.reminder",
                NotificationEvent.created_at >= current - timedelta(hours=24),
            )
        )
        if recent is not None:
            continue
        assigned_membership = db.get(EventMembership, task.assigned_membership_id)
        assignee = db.get(User, assigned_membership.user_id) if assigned_membership else None
        assignee_preferences = db.get(UserNotificationPreference, assignee.id) if assignee else None
        if assignee_preferences is not None and (
            not assignee_preferences.in_app_enabled
            or _in_quiet_hours(assignee_preferences, current)
        ):
            continue
        reminder_label = "Overdue task" if due_at < current else "Upcoming task"
        db.add(
            NotificationEvent(
                template_code="EVENT_STAFF_TASK_REMINDER",
                workflow_code="EVENTS",
                event_type="event_staff_task.reminder",
                entity_type="event_staff_task",
                entity_id=task.id,
                actor="system",
                channel="in_app",
                recipient_strategy="actor",
                resolved_recipients=list(
                    {
                        *([assignee.email] if assignee else []),
                        *_event_admin_emails(db, task.event_id),
                    }
                ),
                subject=f"{reminder_label}: {task.title}",
                body=(
                    f"{reminder_label} is due {due_at.isoformat()} and is still " f"{task.status}."
                ),
                action_href=_task_action_href(task),
                status="queued",
                created_at=current,
            )
        )
        created += 1
    db.commit()
    return created
