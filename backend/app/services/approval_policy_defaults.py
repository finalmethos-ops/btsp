from typing import Final

from app.schemas.configuration_entry import ConfigEntryWrite

APPROVAL_CONFIGURATION_NAMESPACE: Final = "workflow.bpp_purchasing.approvals"

APPROVAL_PERMISSION_DEFINITIONS: Final[dict[str, str]] = {
    "workflow.bpp.regional_approve": "Approve a BPP request at regional review.",
    "workflow.bpp.policy_manage": "Manage BPP approval policy configuration.",
    "workflow.bpp.policy_read": "Evaluate and read BPP approval policies.",
}

BPP_APPROVAL_CONFIGURATION_DEFAULTS: Final[tuple[ConfigEntryWrite, ...]] = (
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.executive_threshold",
        value={
            "amount": 50000,
            "approval_level": "executive",
            "required_permission": "workflow.bpp.executive_approve",
        },
        description="Require executive approval at or above the configured amount.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.regional_threshold",
        value={
            "amount": 25000,
            "approval_level": "regional",
            "required_permission": "workflow.bpp.regional_approve",
        },
        description="Require regional approval at or above the configured amount.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.department_default",
        value={
            "approval_level": "department",
            "required_permission": "workflow.bpp.department_review",
        },
        description="Default approval for submitted BPP purchasing requests.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.restricted_vendors",
        value={"vendor_codes": []},
        description="Vendor codes requiring purchasing review.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.restricted_categories",
        value={"product_categories": []},
        description="Product categories requiring purchasing review.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP_PURCHASING",
        key="approval.enabled",
        value={"enabled": True},
        description="Enable BPP purchasing approval policy evaluation.",
        updated_by="system",
    ),
)
