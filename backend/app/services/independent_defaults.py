from typing import Final

from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.notification import NotificationTemplateCreate

INDEPENDENT_APPROVAL_DEFAULTS: Final[tuple[ConfigEntryWrite, ...]] = (
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.enabled",
        value={"enabled": True},
        description="Enable Independent approval policies.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.store_default",
        value={
            "approval_level": "store",
            "required_permission": "workflow.ind.review",
        },
        description="Default Independent store review.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.regional_threshold",
        value={
            "amount": 25000,
            "approval_level": "regional",
            "required_permission": "workflow.ind.regional_approve",
        },
        description="Independent regional dollar threshold.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.franchise_spending_limit",
        value={
            "amount": 10000,
            "approval_level": "franchise",
            "required_permission": "workflow.ind.franchise_approve",
        },
        description="Independent franchise spending limit.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.store_credit_limit",
        value={
            "amount": 7500,
            "approval_level": "franchise",
            "required_permission": "workflow.ind.franchise_approve",
        },
        description="Default Independent store credit limit.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.restricted_vendors",
        value={"vendor_codes": []},
        description="Independent vendors requiring franchise approval.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.restricted_categories",
        value={"product_categories": []},
        description="Independent categories requiring franchise approval.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="approval.regional_override",
        value={
            "approval_level": "executive",
            "required_permission": "system.admin",
        },
        description="Escalate approved regional overrides to executive review.",
        updated_by="system",
    ),
)


def _template(
    template_code: str,
    event_type: str,
    subject: str,
    body: str,
    *,
    actor: bool = False,
) -> NotificationTemplateCreate:
    return NotificationTemplateCreate(
        template_code=template_code,
        workflow_code="IND_PURCHASING",
        event_type=event_type,
        channel="in_app",
        subject_template=subject,
        body_template=body,
        recipient_strategy="actor" if actor else "workflow_role",
        recipient_config={} if actor else {"role_codes": ["INDEPENDENT_ADMIN"]},
        is_active=True,
    )


INDEPENDENT_NOTIFICATION_TEMPLATES: Final[tuple[NotificationTemplateCreate, ...]] = (
    _template(
        "IND_SUBMITTED_IN_APP",
        "ind.submitted",
        "Independent request {entity_id} submitted",
        "{actor} submitted Independent request {entity_id}.",
    ),
    _template(
        "IND_APPROVED_IN_APP",
        "ind.approved",
        "Independent request {entity_id} approved",
        "Independent request {entity_id} was approved.",
        actor=True,
    ),
    _template(
        "IND_REVISION_REQUESTED_IN_APP",
        "ind.revision_requested",
        "Revision requested for {entity_id}",
        "Independent request {entity_id} requires revision.",
        actor=True,
    ),
    _template(
        "IND_REJECTED_IN_APP",
        "ind.rejected",
        "Independent request {entity_id} rejected",
        "Independent request {entity_id} was rejected.",
        actor=True,
    ),
    _template(
        "IND_PO_CREATED_IN_APP",
        "ind.po_created",
        "Purchase order created for {entity_id}",
        "An Independent purchase order was created for {entity_id}.",
    ),
    _template(
        "IND_VENDOR_SUBMITTED_IN_APP",
        "ind.vendor_submitted",
        "Independent order {entity_id} sent to vendor",
        "Independent order {entity_id} was submitted to the vendor.",
    ),
    _template(
        "IND_VENDOR_CONFIRMED_IN_APP",
        "ind.vendor_confirmed",
        "Vendor acknowledged {entity_id}",
        "The vendor acknowledged Independent order {entity_id}.",
    ),
    _template(
        "IND_RECEIVING_IN_APP",
        "ind.receiving",
        "Independent order {entity_id} ready for receiving",
        "Independent order {entity_id} is ready for receiving.",
    ),
    _template(
        "IND_COMPLETED_IN_APP",
        "ind.completed",
        "Independent order {entity_id} completed",
        "Independent order {entity_id} completed receiving.",
        actor=True,
    ),
)
