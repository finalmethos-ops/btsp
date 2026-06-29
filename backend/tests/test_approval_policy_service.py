from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission  # noqa: F401
from app.models.store import Store  # noqa: F401
from app.models.workflow import WorkflowDefinition  # noqa: F401
from app.schemas.approval_policy import ApprovalLevel, ApprovalPolicyInput
from app.services.approval_policy_defaults import BPP_APPROVAL_CONFIGURATION_DEFAULTS
from app.services.approval_policy_service import (
    ApprovalPolicyConfigurationError,
    evaluate_approval_policy,
    seed_bpp_approval_defaults,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def policy_input(
    amount: str,
    *,
    vendor_code: str | None = None,
    product_category: str | None = None,
) -> ApprovalPolicyInput:
    return ApprovalPolicyInput(
        workflow_code="BPP_PURCHASING",
        entity_type="purchase_request",
        entity_id="PR-2001",
        request_amount=Decimal(amount),
        region_code="SOUTHEAST",
        store_number="1001",
        vendor_code=vendor_code,
        product_category=product_category,
        buying_group_code="BPP",
        submitted_by="requester@example.com",
        context={"source": "test"},
    )


def update_config(db: Session, key: str, value: dict[str, object]) -> None:
    entry = db.scalar(
        select(ConfigurationEntry).where(
            ConfigurationEntry.scope_type == "workflow",
            ConfigurationEntry.scope_key == "BPP_PURCHASING",
            ConfigurationEntry.key == key,
        )
    )
    assert entry is not None
    entry.value = value
    db.commit()


def test_executive_threshold_is_matched_at_50000(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")

    result = evaluate_approval_policy(db, policy_input("50000"))

    assert result.approval_level == ApprovalLevel.EXECUTIVE
    assert result.required_permission == "workflow.bpp.executive_approve"
    assert "executive_threshold" in result.matched_policy_codes


def test_regional_threshold_is_matched_at_25000(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")

    result = evaluate_approval_policy(db, policy_input("25000"))

    assert result.approval_level == ApprovalLevel.REGIONAL
    assert result.required_permission == "workflow.bpp.regional_approve"
    assert "regional_threshold" in result.matched_policy_codes


def test_executive_outranks_regional_when_both_match(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")

    result = evaluate_approval_policy(db, policy_input("75000"))

    assert result.approval_level == ApprovalLevel.EXECUTIVE
    assert result.matched_policy_codes[:2] == ["executive_threshold", "regional_threshold"]


def test_restricted_vendor_triggers_purchasing_review(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")
    update_config(
        db,
        "approval.restricted_vendors",
        {"vendor_codes": ["VENDOR-RESTRICTED"]},
    )

    result = evaluate_approval_policy(
        db,
        policy_input("100", vendor_code="VENDOR-RESTRICTED"),
    )

    assert result.approval_level == ApprovalLevel.PURCHASING
    assert "vendor_restricted" in result.matched_policy_codes


def test_restricted_category_triggers_purchasing_review(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")
    update_config(
        db,
        "approval.restricted_categories",
        {"product_categories": ["CONTROLLED"]},
    )

    result = evaluate_approval_policy(
        db,
        policy_input("100", product_category="CONTROLLED"),
    )

    assert result.approval_level == ApprovalLevel.PURCHASING
    assert "category_restricted" in result.matched_policy_codes


def test_department_default_applies_without_higher_match(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")

    result = evaluate_approval_policy(db, policy_input("100"))

    assert result.requires_approval is True
    assert result.approval_level == ApprovalLevel.DEPARTMENT
    assert result.matched_policy_codes == ["department_default"]


def test_disabled_policy_returns_no_approval(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")
    update_config(db, "approval.enabled", {"enabled": False})

    result = evaluate_approval_policy(db, policy_input("75000"))

    assert result.requires_approval is False
    assert result.approval_level == ApprovalLevel.NONE
    assert result.required_permission is None
    assert result.matched_policy_codes == []
    snapshot_count = db.scalar(
        select(func.count())
        .select_from(EventSnapshot)
        .where(EventSnapshot.event_type == "approval.policy.matched")
    )
    assert snapshot_count == 0


def test_policy_evaluation_snapshot_payload_is_correct(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")

    result = evaluate_approval_policy(db, policy_input("50000"))
    snapshot = db.scalar(
        select(EventSnapshot).where(EventSnapshot.event_type == "approval.policy.matched")
    )

    assert snapshot is not None
    assert snapshot.entity_type == "purchase_request"
    assert snapshot.entity_id == "PR-2001"
    assert snapshot.actor == "requester@example.com"
    assert snapshot.payload == {
        "workflow_code": "BPP_PURCHASING",
        "approval_level": "executive",
        "approval_reason": result.approval_reason,
        "required_permission": "workflow.bpp.executive_approve",
        "matched_policy_codes": [
            "executive_threshold",
            "regional_threshold",
            "department_default",
        ],
    }


def test_missing_required_configuration_fails_safely(db: Session) -> None:
    seed_bpp_approval_defaults(db, actor="admin@example.com")
    entry = db.scalar(
        select(ConfigurationEntry).where(ConfigurationEntry.key == "approval.regional_threshold")
    )
    assert entry is not None
    db.delete(entry)
    db.commit()

    with pytest.raises(
        ApprovalPolicyConfigurationError,
        match="approval.regional_threshold",
    ):
        evaluate_approval_policy(db, policy_input("50000"))


def test_approval_default_seed_is_idempotent(db: Session) -> None:
    first = seed_bpp_approval_defaults(db, actor="admin@example.com")
    second = seed_bpp_approval_defaults(db, actor="admin@example.com")

    assert first == second == len(BPP_APPROVAL_CONFIGURATION_DEFAULTS)
    count = db.scalar(
        select(func.count())
        .select_from(ConfigurationEntry)
        .where(ConfigurationEntry.key.like("approval.%"))
    )
    assert count == len(BPP_APPROVAL_CONFIGURATION_DEFAULTS)
