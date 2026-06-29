from typing import Final

from app.core.workflows import WorkflowCode
from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.flow import FlowDefinitionWrite, FlowRule

INDEPENDENT_PERMISSION_DEFINITIONS: Final[dict[str, str]] = {
    "workflow.ind.submit": "Submit an Independent purchasing request.",
    "workflow.ind.review": "Review or revise an Independent purchasing request.",
    "workflow.ind.franchise_approve": "Approve an Independent request for the franchise.",
    "workflow.ind.regional_approve": "Approve an Independent request at regional review.",
    "workflow.ind.vendor_select": "Select a vendor for an Independent request.",
    "workflow.ind.receive": "Acknowledge, schedule, and receive an Independent order.",
    "workflow.ind.cancel": "Cancel an Independent purchasing request.",
    "workflow.ind.reject": "Reject an Independent purchasing request.",
}

INDEPENDENT_PURCHASING_STATES: Final[tuple[str, ...]] = (
    "draft",
    "store_review",
    "franchise_review",
    "vendor_selection",
    "pricing_review",
    "regional_approval",
    "po_created",
    "vendor_submission",
    "vendor_acknowledged",
    "shipment_scheduled",
    "receiving",
    "completed",
    "revision_requested",
    "rejected",
    "cancelled",
    "expired",
)

INDEPENDENT_PURCHASING_TERMINAL_STATES: Final[tuple[str, ...]] = (
    "completed",
    "rejected",
    "cancelled",
    "expired",
)


def _rule(action: str, source: str, target: str, permission: str) -> FlowRule:
    return FlowRule(action=action, source=source, target=target, permission=permission)


INDEPENDENT_PURCHASING_RULES: Final[tuple[FlowRule, ...]] = (
    _rule("submit_for_store_review", "draft", "store_review", "workflow.ind.submit"),
    _rule("store_approve", "store_review", "franchise_review", "workflow.ind.review"),
    _rule(
        "franchise_approve",
        "franchise_review",
        "vendor_selection",
        "workflow.ind.franchise_approve",
    ),
    _rule(
        "select_vendor",
        "vendor_selection",
        "pricing_review",
        "workflow.ind.vendor_select",
    ),
    _rule("verify_pricing", "pricing_review", "regional_approval", "workflow.ind.review"),
    _rule(
        "regional_approve",
        "regional_approval",
        "po_created",
        "workflow.ind.regional_approve",
    ),
    _rule("generate_po", "po_created", "vendor_submission", "workflow.ind.review"),
    _rule(
        "submit_to_vendor",
        "vendor_submission",
        "vendor_acknowledged",
        "workflow.ind.review",
    ),
    _rule(
        "acknowledge_vendor",
        "vendor_acknowledged",
        "shipment_scheduled",
        "workflow.ind.receive",
    ),
    _rule(
        "schedule_shipment",
        "shipment_scheduled",
        "receiving",
        "workflow.ind.receive",
    ),
    _rule("receive_order", "receiving", "completed", "workflow.ind.receive"),
    *(
        _rule("return_for_revision", source, "revision_requested", "workflow.ind.review")
        for source in (
            "store_review",
            "franchise_review",
            "vendor_selection",
            "pricing_review",
            "regional_approval",
        )
    ),
    _rule("resubmit", "revision_requested", "store_review", "workflow.ind.submit"),
    *(
        _rule("reject", source, "rejected", "workflow.ind.reject")
        for source in ("store_review", "franchise_review", "regional_approval")
    ),
    *(
        _rule("cancel", source, "cancelled", "workflow.ind.cancel")
        for source in ("draft", "revision_requested")
    ),
    *(
        _rule("expire", source, "expired", "workflow.ind.review")
        for source in ("store_review", "franchise_review", "regional_approval")
    ),
    *(
        _rule("administrative_reopen", source, "draft", "system.admin")
        for source in ("rejected", "cancelled", "expired")
    ),
)

INDEPENDENT_PURCHASING_DEFINITION: Final = FlowDefinitionWrite(
    code=WorkflowCode.IND_PURCHASING,
    name="Independent Purchasing",
    version=1,
    business_area="Purchasing",
    category="Independent Ordering",
    configuration_namespace="workflow.ind_purchasing",
    states=list(INDEPENDENT_PURCHASING_STATES),
    initial_state="draft",
    terminal_states=list(INDEPENDENT_PURCHASING_TERMINAL_STATES),
    rules=list(INDEPENDENT_PURCHASING_RULES),
    is_active=True,
)

INDEPENDENT_CONFIGURATION_DEFAULTS: Final[tuple[ConfigEntryWrite, ...]] = (
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="enabled",
        value={"enabled": True},
        description="Enable Independent purchasing.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="regional_threshold",
        value={"amount": 25000},
        description="Independent regional approval threshold.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="franchise_threshold",
        value={"amount": 10000},
        description="Independent franchise approval threshold.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="allow_revision",
        value={"enabled": True},
        description="Allow Independent purchasing revisions.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="allow_cancel",
        value={"enabled": True},
        description="Allow Independent purchasing cancellation.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="notification.enabled",
        value={"enabled": True},
        description="Enable Independent purchasing notifications.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="IND_PURCHASING",
        key="notification.channels",
        value={"channels": ["in_app", "email"]},
        description="Independent purchasing notification channels.",
        updated_by="system",
    ),
)
