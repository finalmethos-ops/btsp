from decimal import Decimal, InvalidOperation
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import ConfigurationEntry
from app.schemas.approval_policy import (
    ApprovalLevel,
    ApprovalPolicyInput,
    ApprovalPolicyMatch,
    ApprovalPolicyResult,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.approval_policy_defaults import BPP_APPROVAL_CONFIGURATION_DEFAULTS
from app.services.bpp_purchasing_seed_service import seed_bpp_permissions
from app.services.configuration_service import upsert_config_entry
from app.services.snapshot_service import append_snapshot


class ApprovalPolicyConfigurationError(ValueError):
    pass


APPROVAL_LEVEL_RANK: Final[dict[ApprovalLevel, int]] = {
    ApprovalLevel.NONE: 0,
    ApprovalLevel.STORE: 1,
    ApprovalLevel.DEPARTMENT: 1,
    ApprovalLevel.FRANCHISE: 2,
    ApprovalLevel.PURCHASING: 2,
    ApprovalLevel.REGIONAL: 3,
    ApprovalLevel.EXECUTIVE: 4,
    ApprovalLevel.SYSTEM_ADMIN: 5,
}

ROUTING_GROUPS: Final[dict[ApprovalLevel, str]] = {
    ApprovalLevel.STORE: "ind.store_approvers",
    ApprovalLevel.DEPARTMENT: "bpp.department_approvers",
    ApprovalLevel.FRANCHISE: "ind.franchise_approvers",
    ApprovalLevel.PURCHASING: "bpp.purchasing_approvers",
    ApprovalLevel.REGIONAL: "bpp.regional_approvers",
    ApprovalLevel.EXECUTIVE: "bpp.executive_approvers",
    ApprovalLevel.SYSTEM_ADMIN: "system.administrators",
}

REQUIRED_APPROVAL_CONFIG_KEYS: Final = {
    "approval.executive_threshold",
    "approval.regional_threshold",
    "approval.department_default",
    "approval.restricted_vendors",
    "approval.restricted_categories",
}

REQUIRED_INDEPENDENT_APPROVAL_CONFIG_KEYS: Final = {
    "approval.store_default",
    "approval.regional_threshold",
    "approval.franchise_spending_limit",
    "approval.store_credit_limit",
    "approval.restricted_vendors",
    "approval.restricted_categories",
    "approval.regional_override",
}


def load_workflow_approval_config(
    db: Session,
    workflow_code: str,
) -> dict[str, dict[str, Any]]:
    if workflow_code not in {"BPP_PURCHASING", "IND_PURCHASING"}:
        raise ApprovalPolicyConfigurationError(
            f"Approval policies are not supported for workflow: {workflow_code}"
        )

    entries = db.scalars(
        select(ConfigurationEntry).where(
            ConfigurationEntry.scope_type == "workflow",
            ConfigurationEntry.scope_key == workflow_code,
            ConfigurationEntry.key.like("approval.%"),
            ConfigurationEntry.is_active.is_(True),
        )
    ).all()
    config = {entry.key: entry.value for entry in entries}
    enabled = config.get("approval.enabled")
    if not isinstance(enabled, dict) or not isinstance(enabled.get("enabled"), bool):
        raise ApprovalPolicyConfigurationError("Missing or invalid configuration: approval.enabled")
    if not enabled["enabled"]:
        return config

    required_keys = (
        REQUIRED_APPROVAL_CONFIG_KEYS
        if workflow_code == "BPP_PURCHASING"
        else REQUIRED_INDEPENDENT_APPROVAL_CONFIG_KEYS
    )
    missing = required_keys.difference(config)
    if missing:
        missing_keys = ", ".join(sorted(missing))
        raise ApprovalPolicyConfigurationError(f"Missing approval configuration: {missing_keys}")
    return config


def _configured_match(
    policy_code: str,
    policy: dict[str, Any],
    reason: str,
) -> ApprovalPolicyMatch:
    try:
        level = ApprovalLevel(policy["approval_level"])
        permission = policy["required_permission"]
        routing_group = ROUTING_GROUPS[level]
    except (KeyError, ValueError) as exc:
        raise ApprovalPolicyConfigurationError(
            f"Invalid approval configuration: {policy_code}"
        ) from exc
    if not isinstance(permission, str) or not permission:
        raise ApprovalPolicyConfigurationError(
            f"Invalid required permission configuration: {policy_code}"
        )
    return ApprovalPolicyMatch(
        policy_code=policy_code,
        approval_level=level,
        approval_reason=reason,
        required_permission=permission,
        routing_group=routing_group,
    )


def match_threshold_policies(
    payload: ApprovalPolicyInput,
    config: dict[str, dict[str, Any]],
) -> list[ApprovalPolicyMatch]:
    matches: list[ApprovalPolicyMatch] = []
    policies = (
        ("approval.executive_threshold", "executive_threshold"),
        ("approval.regional_threshold", "regional_threshold"),
    )
    for config_key, policy_code in policies:
        policy = config[config_key]
        try:
            threshold = Decimal(str(policy["amount"]))
        except (KeyError, InvalidOperation) as exc:
            raise ApprovalPolicyConfigurationError(
                f"Invalid threshold configuration: {config_key}"
            ) from exc
        if payload.request_amount >= threshold:
            matches.append(
                _configured_match(
                    policy_code,
                    policy,
                    f"Request amount {payload.request_amount} meets {policy_code} at {threshold}.",
                )
            )
    return matches


def match_vendor_policies(
    payload: ApprovalPolicyInput,
    config: dict[str, dict[str, Any]],
) -> list[ApprovalPolicyMatch]:
    policy = config["approval.restricted_vendors"]
    vendor_codes = policy.get("vendor_codes")
    if not isinstance(vendor_codes, list):
        raise ApprovalPolicyConfigurationError(
            "Invalid approval configuration: approval.restricted_vendors"
        )
    if payload.vendor_code is None or payload.vendor_code not in vendor_codes:
        return []
    return [
        ApprovalPolicyMatch(
            policy_code="vendor_restricted",
            approval_level=ApprovalLevel.PURCHASING,
            approval_reason=f"Vendor {payload.vendor_code} is restricted.",
            required_permission="workflow.bpp.purchasing_review",
            routing_group=ROUTING_GROUPS[ApprovalLevel.PURCHASING],
        )
    ]


def match_category_policies(
    payload: ApprovalPolicyInput,
    config: dict[str, dict[str, Any]],
) -> list[ApprovalPolicyMatch]:
    policy = config["approval.restricted_categories"]
    categories = policy.get("product_categories")
    if not isinstance(categories, list):
        raise ApprovalPolicyConfigurationError(
            "Invalid approval configuration: approval.restricted_categories"
        )
    if payload.product_category is None or payload.product_category not in categories:
        return []
    return [
        ApprovalPolicyMatch(
            policy_code="category_restricted",
            approval_level=ApprovalLevel.PURCHASING,
            approval_reason=f"Product category {payload.product_category} is restricted.",
            required_permission="workflow.bpp.purchasing_review",
            routing_group=ROUTING_GROUPS[ApprovalLevel.PURCHASING],
        )
    ]


def return_highest_required_approval(
    matches: list[ApprovalPolicyMatch],
) -> ApprovalPolicyMatch | None:
    if not matches:
        return None
    return max(matches, key=lambda match: APPROVAL_LEVEL_RANK[match.approval_level])


def match_independent_policies(
    payload: ApprovalPolicyInput,
    config: dict[str, dict[str, Any]],
) -> list[ApprovalPolicyMatch]:
    matches = [
        _configured_match(
            "store_default",
            config["approval.store_default"],
            "Store approval is required for submitted Independent requests.",
        )
    ]
    threshold_policies = (
        ("approval.regional_threshold", "regional_threshold"),
        ("approval.franchise_spending_limit", "franchise_spending_limit"),
    )
    for config_key, policy_code in threshold_policies:
        policy = config[config_key]
        try:
            threshold = Decimal(str(policy["amount"]))
        except (KeyError, InvalidOperation) as exc:
            raise ApprovalPolicyConfigurationError(
                f"Invalid threshold configuration: {config_key}"
            ) from exc
        if payload.request_amount >= threshold:
            matches.append(
                _configured_match(
                    policy_code,
                    policy,
                    f"Request amount {payload.request_amount} meets {policy_code} at {threshold}.",
                )
            )

    credit_policy = config["approval.store_credit_limit"]
    configured_credit = credit_policy.get("amount")
    credit_value = payload.context.get("store_credit_limit", configured_credit)
    try:
        credit_limit = Decimal(str(credit_value))
    except InvalidOperation as exc:
        raise ApprovalPolicyConfigurationError(
            "Invalid threshold configuration: approval.store_credit_limit"
        ) from exc
    if payload.request_amount >= credit_limit:
        matches.append(
            _configured_match(
                "store_credit_limit",
                credit_policy,
                f"Request amount {payload.request_amount} meets store credit limit {credit_limit}.",
            )
        )

    vendors = config["approval.restricted_vendors"].get("vendor_codes")
    if not isinstance(vendors, list):
        raise ApprovalPolicyConfigurationError(
            "Invalid approval configuration: approval.restricted_vendors"
        )
    if payload.vendor_code is not None and payload.vendor_code in vendors:
        matches.append(
            ApprovalPolicyMatch(
                policy_code="vendor_restriction",
                approval_level=ApprovalLevel.FRANCHISE,
                approval_reason=f"Vendor {payload.vendor_code} is restricted.",
                required_permission="workflow.ind.franchise_approve",
                routing_group=ROUTING_GROUPS[ApprovalLevel.FRANCHISE],
            )
        )

    categories = config["approval.restricted_categories"].get("product_categories")
    if not isinstance(categories, list):
        raise ApprovalPolicyConfigurationError(
            "Invalid approval configuration: approval.restricted_categories"
        )
    if payload.product_category is not None and payload.product_category in categories:
        matches.append(
            ApprovalPolicyMatch(
                policy_code="restricted_categories",
                approval_level=ApprovalLevel.FRANCHISE,
                approval_reason=f"Product category {payload.product_category} is restricted.",
                required_permission="workflow.ind.franchise_approve",
                routing_group=ROUTING_GROUPS[ApprovalLevel.FRANCHISE],
            )
        )

    if payload.context.get("regional_override") is True:
        override = _configured_match(
            "regional_override",
            config["approval.regional_override"],
            "Regional override requires executive review.",
        )
        matches.append(override.model_copy(update={"routing_group": "system.administrators"}))
    return matches


def evaluate_approval_policy(
    db: Session,
    payload: ApprovalPolicyInput,
) -> ApprovalPolicyResult:
    config = load_workflow_approval_config(db, payload.workflow_code)
    if not config["approval.enabled"]["enabled"]:
        return ApprovalPolicyResult(
            requires_approval=False,
            approval_level=ApprovalLevel.NONE,
            approval_reason="Approval policies are disabled.",
            required_permission=None,
            routing_group=None,
            matched_policy_codes=[],
        )

    if payload.workflow_code == "BPP_PURCHASING":
        matches = [
            _configured_match(
                "department_default",
                config["approval.department_default"],
                "Department approval is required for submitted BPP requests.",
            ),
            *match_threshold_policies(payload, config),
            *match_vendor_policies(payload, config),
            *match_category_policies(payload, config),
        ]
    else:
        matches = match_independent_policies(payload, config)
    highest = return_highest_required_approval(matches)
    if highest is None:
        raise ApprovalPolicyConfigurationError("No approval policy matched")

    ordered_matches = sorted(
        matches,
        key=lambda match: APPROVAL_LEVEL_RANK[match.approval_level],
        reverse=True,
    )
    result = ApprovalPolicyResult(
        requires_approval=True,
        approval_level=highest.approval_level,
        approval_reason=highest.approval_reason,
        required_permission=highest.required_permission,
        routing_group=highest.routing_group,
        matched_policy_codes=[match.policy_code for match in ordered_matches],
    )
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="approval.policy.matched",
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            actor=payload.submitted_by,
            payload={
                "workflow_code": payload.workflow_code,
                "approval_level": result.approval_level,
                "approval_reason": result.approval_reason,
                "required_permission": result.required_permission,
                "matched_policy_codes": result.matched_policy_codes,
            },
        ),
    )
    return result


def seed_bpp_approval_defaults(db: Session, actor: str) -> int:
    seed_bpp_permissions(db)
    for default in BPP_APPROVAL_CONFIGURATION_DEFAULTS:
        payload = default.model_copy(deep=True, update={"updated_by": actor})
        upsert_config_entry(db, payload)
    return len(BPP_APPROVAL_CONFIGURATION_DEFAULTS)
