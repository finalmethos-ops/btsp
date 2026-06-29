import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission  # noqa: F401
from app.models.notification import NotificationEvent, NotificationTemplate
from app.models.store import Store  # noqa: F401
from app.models.workflow import WorkflowDefinition  # noqa: F401
from app.schemas.notification import (
    NotificationChannel,
    NotificationEmitInput,
    NotificationEventResponse,
    NotificationStatus,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    RecipientStrategy,
)
from app.services.notification_defaults import (
    BPP_NOTIFICATION_CONFIGURATION_DEFAULTS,
    BPP_NOTIFICATION_TEMPLATES,
)
from app.services.notification_service import (
    create_notification_template,
    emit_notification,
    mark_notification_failed,
    render_template,
    resolve_recipients,
    retry_notification_event,
    seed_bpp_notification_defaults,
    update_notification_template,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def template_payload(
    code: str = "TEST_IN_APP",
    *,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    strategy: RecipientStrategy = RecipientStrategy.ACTOR,
    active: bool = True,
) -> NotificationTemplateCreate:
    return NotificationTemplateCreate(
        template_code=code,
        workflow_code="BPP_PURCHASING",
        event_type="bpp.submitted",
        channel=channel,
        subject_template="Request {entity_id}: {title}",
        body_template="{actor} submitted {title} for {amount}.",
        recipient_strategy=strategy,
        recipient_config={},
        is_active=active,
    )


def emit_payload() -> NotificationEmitInput:
    return NotificationEmitInput(
        workflow_code="BPP_PURCHASING",
        event_type="bpp.submitted",
        entity_type="purchase_request",
        entity_id="PR-3001",
        actor="requester@example.com",
        context={"title": "Store fixtures", "amount": 1250},
    )


def test_template_can_be_created(db: Session) -> None:
    template = create_notification_template(db, template_payload())

    assert template.id is not None
    assert template.template_code == "TEST_IN_APP"


def test_template_can_be_updated(db: Session) -> None:
    create_notification_template(db, template_payload())

    template = update_notification_template(
        db,
        "TEST_IN_APP",
        NotificationTemplateUpdate(subject_template="Updated {entity_id}"),
    )

    assert template is not None
    assert template.subject_template == "Updated {entity_id}"


def test_template_rejects_complex_format_expressions() -> None:
    with pytest.raises(ValueError, match="simple names"):
        NotificationTemplateCreate(
            **{
                **template_payload().model_dump(),
                "subject_template": "Unsafe {actor.__class__}",
            }
        )


def test_inactive_template_is_skipped(db: Session) -> None:
    create_notification_template(db, template_payload(active=False))

    events = emit_notification(db, emit_payload())

    assert len(events) == 1
    assert events[0].status == NotificationStatus.SKIPPED


def test_notification_rendering_substitutes_context_values(db: Session) -> None:
    template = create_notification_template(db, template_payload())

    subject, body = render_template(template, emit_payload())

    assert subject == "Request PR-3001: Store fixtures"
    assert body == "requester@example.com submitted Store fixtures for 1250."


def test_actor_recipient_strategy_resolves(db: Session) -> None:
    recipients = resolve_recipients(
        db,
        RecipientStrategy.ACTOR,
        {},
        emit_payload(),
    )

    assert recipients == ["requester@example.com"]


def test_static_recipient_strategy_resolves_unique_sorted_values(db: Session) -> None:
    recipients = resolve_recipients(
        db,
        RecipientStrategy.STATIC_RECIPIENTS,
        {"recipients": ["b@example.com", "a@example.com", "b@example.com"]},
        emit_payload(),
    )

    assert recipients == ["a@example.com", "b@example.com"]


def test_in_app_notification_event_is_queued(db: Session) -> None:
    create_notification_template(db, template_payload())

    event = emit_notification(db, emit_payload())[0]
    response = NotificationEventResponse.model_validate(event)

    assert event.status == NotificationStatus.QUEUED
    assert event.resolved_recipients == ["requester@example.com"]
    assert response.notification_id == event.id


def test_failed_rendered_notification_can_be_requeued_by_admin(db: Session) -> None:
    create_notification_template(db, template_payload())
    event = emit_notification(db, emit_payload())[0]
    mark_notification_failed(db, event.id, "Temporary provider failure")

    retried = retry_notification_event(db, event.id, "admin@example.com")

    assert retried is not None
    assert retried.status == NotificationStatus.QUEUED
    assert retried.error_message is None
    audit = db.scalar(
        select(EventSnapshot).where(EventSnapshot.event_type == "admin.notification.requeued")
    )
    assert audit is not None
    assert audit.actor == "admin@example.com"


def test_email_notification_is_stubbed_as_queued(db: Session) -> None:
    create_notification_template(
        db,
        template_payload(code="TEST_EMAIL", channel=NotificationChannel.EMAIL),
    )

    event = emit_notification(db, emit_payload())[0]

    assert event.channel == NotificationChannel.EMAIL
    assert event.status == NotificationStatus.QUEUED


def test_webhook_notification_is_skipped_when_disabled(db: Session) -> None:
    create_notification_template(
        db,
        template_payload(code="TEST_WEBHOOK", channel=NotificationChannel.WEBHOOK),
    )

    event = emit_notification(db, emit_payload())[0]

    assert event.channel == NotificationChannel.WEBHOOK
    assert event.status == NotificationStatus.SKIPPED


def test_notification_emitted_snapshot_is_created(db: Session) -> None:
    create_notification_template(db, template_payload())

    event = emit_notification(db, emit_payload())[0]
    snapshot = db.scalar(
        select(EventSnapshot).where(EventSnapshot.event_type == "notification.emitted")
    )

    assert snapshot is not None
    assert snapshot.entity_type == "purchase_request"
    assert snapshot.entity_id == "PR-3001"
    assert snapshot.actor == "requester@example.com"
    assert snapshot.payload == {
        "workflow_code": "BPP_PURCHASING",
        "event_type": "bpp.submitted",
        "template_code": "TEST_IN_APP",
        "channel": "in_app",
        "recipient_strategy": "actor",
        "status": "queued",
    }
    assert event.id is not None


def test_bpp_default_templates_seed_idempotently(db: Session) -> None:
    first = seed_bpp_notification_defaults(db, actor="admin@example.com")
    second = seed_bpp_notification_defaults(db, actor="admin@example.com")

    assert (
        first
        == second
        == (
            len(BPP_NOTIFICATION_CONFIGURATION_DEFAULTS),
            len(BPP_NOTIFICATION_TEMPLATES),
        )
    )
    assert db.scalar(select(func.count()).select_from(NotificationTemplate)) == len(
        BPP_NOTIFICATION_TEMPLATES
    )
    assert db.scalar(
        select(func.count())
        .select_from(ConfigurationEntry)
        .where(ConfigurationEntry.key.like("notification.%"))
    ) == len(BPP_NOTIFICATION_CONFIGURATION_DEFAULTS)
    assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 0
