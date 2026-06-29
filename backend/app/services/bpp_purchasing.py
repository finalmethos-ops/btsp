from typing import Final

from app.core.workflows import WorkflowCode
from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.flow import FlowDefinitionWrite, FlowRule
from app.services.approval_policy_defaults import APPROVAL_PERMISSION_DEFINITIONS
from app.services.notification_defaults import BPP_NOTIFICATION_PERMISSION_DEFINITIONS

BPP_PURCHASING_STATES: Final[tuple[str, ...]] = (
    "draft",
    "department_review",
    "purchasing_review",
    "vendor_selection",
    "cost_verification",
    "executive_approval",
    "po_created",
    "vendor_submission",
    "vendor_confirmed",
    "shipment_scheduled",
    "receiving",
    "completed",
    "revision_requested",
    "rejected",
    "cancelled",
    "expired",
)

BPP_PURCHASING_TERMINAL_STATES: Final[tuple[str, ...]] = (
    "completed",
    "rejected",
    "cancelled",
    "expired",
)

BPP_PERMISSION_DEFINITIONS: Final[dict[str, str]] = {
    "workflow.bpp.submit": "Submit a BPP purchasing request for department review.",
    "workflow.bpp.department_review": "Approve a BPP request at department review.",
    "workflow.bpp.purchasing_review": "Approve a BPP request at purchasing review.",
    "workflow.bpp.vendor_select": "Select the vendor for a BPP request.",
    "workflow.bpp.cost_verify": "Verify BPP purchasing costs.",
    "workflow.bpp.executive_approve": "Approve a BPP request at executive review.",
    "workflow.bpp.po_generate": "Generate a purchase order for a BPP request.",
    "workflow.bpp.vendor_submit": "Submit a BPP purchase order to a vendor.",
    "workflow.bpp.vendor_confirm": "Record vendor confirmation for a BPP order.",
    "workflow.bpp.shipment_schedule": "Schedule shipment for a BPP order.",
    "workflow.bpp.receive": "Receive and complete a BPP order.",
    "workflow.bpp.revise": "Return or resubmit a BPP request for revision.",
    "workflow.bpp.reject": "Reject a BPP purchasing request.",
    "workflow.bpp.cancel": "Cancel a BPP purchasing request.",
    "workflow.bpp.expire": "Expire a BPP purchasing request.",
    **APPROVAL_PERMISSION_DEFINITIONS,
    **BPP_NOTIFICATION_PERMISSION_DEFINITIONS,
}


def _rule(action: str, source: str, target: str, permission: str) -> FlowRule:
    return FlowRule(action=action, source=source, target=target, permission=permission)


BPP_PURCHASING_RULES: Final[tuple[FlowRule, ...]] = (
    _rule("submit_for_department_review", "draft", "department_review", "workflow.bpp.submit"),
    _rule(
        "department_approve",
        "department_review",
        "purchasing_review",
        "workflow.bpp.department_review",
    ),
    *(
        _rule("return_for_revision", source, "revision_requested", "workflow.bpp.revise")
        for source in (
            "department_review",
            "purchasing_review",
            "vendor_selection",
            "cost_verification",
            "executive_approval",
        )
    ),
    _rule("resubmit", "revision_requested", "department_review", "workflow.bpp.revise"),
    _rule(
        "purchasing_approve",
        "purchasing_review",
        "vendor_selection",
        "workflow.bpp.purchasing_review",
    ),
    _rule(
        "select_vendor",
        "vendor_selection",
        "cost_verification",
        "workflow.bpp.vendor_select",
    ),
    _rule(
        "verify_cost",
        "cost_verification",
        "executive_approval",
        "workflow.bpp.cost_verify",
    ),
    _rule(
        "executive_approve",
        "executive_approval",
        "po_created",
        "workflow.bpp.executive_approve",
    ),
    _rule("generate_po", "po_created", "vendor_submission", "workflow.bpp.po_generate"),
    _rule(
        "submit_to_vendor",
        "vendor_submission",
        "vendor_confirmed",
        "workflow.bpp.vendor_submit",
    ),
    _rule(
        "confirm_vendor",
        "vendor_confirmed",
        "shipment_scheduled",
        "workflow.bpp.vendor_confirm",
    ),
    _rule(
        "schedule_shipment",
        "shipment_scheduled",
        "receiving",
        "workflow.bpp.shipment_schedule",
    ),
    _rule("receive_order", "receiving", "completed", "workflow.bpp.receive"),
    *(
        _rule("reject", source, "rejected", "workflow.bpp.reject")
        for source in ("department_review", "purchasing_review", "executive_approval")
    ),
    *(
        _rule("cancel", source, "cancelled", "workflow.bpp.cancel")
        for source in ("draft", "revision_requested")
    ),
    *(
        _rule("expire", source, "expired", "workflow.bpp.expire")
        for source in ("department_review", "purchasing_review", "executive_approval")
    ),
)

BPP_PURCHASING_DEFINITION: Final = FlowDefinitionWrite(
    code=WorkflowCode.BPP_PURCHASING,
    name="BPP Purchasing",
    version=1,
    business_area="Purchasing",
    category="BPP Ordering",
    configuration_namespace="workflow.bpp_purchasing",
    states=list(BPP_PURCHASING_STATES),
    initial_state="draft",
    terminal_states=list(BPP_PURCHASING_TERMINAL_STATES),
    rules=list(BPP_PURCHASING_RULES),
    is_active=True,
)

BPP_PURCHASING_CONFIGURATION_DEFAULTS: Final[tuple[ConfigEntryWrite, ...]] = (
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="enabled",
        value={"enabled": True},
        description="Enable the BPP purchasing workflow.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="executive_approval_threshold",
        value={"amount": 50000},
        description="Order value requiring executive approval.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="auto_approval_enabled",
        value={"enabled": False},
        description="Enable automatic approval when future policy permits it.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="allow_revision",
        value={"enabled": True},
        description="Allow requests to enter the revision cycle.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="allow_cancel_from_draft",
        value={"enabled": True},
        description="Allow draft requests to be cancelled.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key=WorkflowCode.BPP_PURCHASING,
        key="notification_enabled",
        value={"enabled": True},
        description="Enable BPP purchasing workflow notifications.",
        updated_by="system",
    ),
)
