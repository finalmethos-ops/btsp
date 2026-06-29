from typing import Final

from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.notification import NotificationTemplateCreate

NOTIFICATION_CONFIGURATION_NAMESPACE: Final = "workflow.bpp_purchasing.notifications"

GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS: Final[dict[str, str]] = {
    "notifications.read": "Read notification templates and event history.",
    "notifications.manage": "Create and update notification templates.",
    "notifications.send": "Emit workflow notifications.",
}

BPP_NOTIFICATION_PERMISSION_DEFINITIONS: Final[dict[str, str]] = {
    "workflow.bpp.notifications.manage": "Seed and manage BPP notification defaults.",
}

BPP_NOTIFICATION_CONFIGURATION_DEFAULTS: Final[tuple[ConfigEntryWrite, ...]] = (
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="notification.enabled",
        value={"enabled": True},
        description="Enable BPP purchasing notifications.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="notification.channels",
        value={"channels": ["in_app", "email"]},
        description="Enabled BPP purchasing notification channels.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="notification.default_channel",
        value={"channel": "in_app"},
        description="Default BPP purchasing notification channel.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="notification.digest_enabled",
        value={"enabled": False},
        description="Enable BPP purchasing notification digests.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="notification.webhook_enabled",
        value={"enabled": False},
        description="Enable BPP purchasing webhook delivery.",
        updated_by="system",
    ),
)


def _in_app_template(
    template_code: str,
    event_type: str,
    subject: str,
    body: str,
    *,
    actor_recipient: bool = False,
) -> NotificationTemplateCreate:
    return NotificationTemplateCreate(
        template_code=template_code,
        workflow_code="BPP_PURCHASING",
        event_type=event_type,
        channel="in_app",
        subject_template=subject,
        body_template=body,
        recipient_strategy="actor" if actor_recipient else "workflow_role",
        recipient_config={} if actor_recipient else {"role_codes": ["BPP_ADMIN"]},
        is_active=True,
    )


BPP_NOTIFICATION_TEMPLATES: Final[tuple[NotificationTemplateCreate, ...]] = (
    _in_app_template(
        "BPP_SUBMITTED_IN_APP",
        "bpp.submitted",
        "BPP request {entity_id} submitted",
        "{actor} submitted BPP request {entity_id} for review.",
    ),
    _in_app_template(
        "BPP_REVISION_REQUESTED_IN_APP",
        "bpp.revision_requested",
        "Revision requested for {entity_id}",
        "A revision was requested for BPP request {entity_id}.",
        actor_recipient=True,
    ),
    _in_app_template(
        "BPP_REJECTED_IN_APP",
        "bpp.rejected",
        "BPP request {entity_id} rejected",
        "BPP request {entity_id} was rejected.",
        actor_recipient=True,
    ),
    _in_app_template(
        "BPP_APPROVED_IN_APP",
        "bpp.approved",
        "BPP request {entity_id} approved",
        "BPP request {entity_id} was approved.",
        actor_recipient=True,
    ),
    _in_app_template(
        "BPP_PO_CREATED_IN_APP",
        "bpp.po_created",
        "Purchase order created for {entity_id}",
        "A purchase order was created for BPP request {entity_id}.",
    ),
    _in_app_template(
        "BPP_VENDOR_SUBMITTED_IN_APP",
        "bpp.vendor_submitted",
        "BPP order {entity_id} sent to vendor",
        "BPP order {entity_id} was submitted to the selected vendor.",
    ),
    _in_app_template(
        "BPP_VENDOR_CONFIRMED_IN_APP",
        "bpp.vendor_confirmed",
        "Vendor confirmed BPP order {entity_id}",
        "The vendor confirmed BPP order {entity_id}.",
    ),
    _in_app_template(
        "BPP_COMPLETED_IN_APP",
        "bpp.completed",
        "BPP order {entity_id} completed",
        "BPP order {entity_id} completed receiving.",
        actor_recipient=True,
    ),
)
