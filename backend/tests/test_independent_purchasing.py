from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.v1.routes.workflow_engine import start_instance
from app.core.workflows import WORKFLOW_REGISTRY, WorkflowLifecycle
from app.db.session import Base
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role, User
from app.models.notification import NotificationEvent, NotificationTemplate
from app.models.store import Store
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.approval_policy import ApprovalLevel, ApprovalPolicyInput
from app.schemas.flow import FlowActionRequest, FlowStartRequest
from app.schemas.notification import NotificationEmitInput, NotificationStatus
from app.services.approval_policy_service import evaluate_approval_policy
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.independent_defaults import (
    INDEPENDENT_APPROVAL_DEFAULTS,
    INDEPENDENT_NOTIFICATION_TEMPLATES,
)
from app.services.independent_purchasing import (
    INDEPENDENT_CONFIGURATION_DEFAULTS,
    INDEPENDENT_PERMISSION_DEFINITIONS,
    INDEPENDENT_PURCHASING_DEFINITION,
    INDEPENDENT_PURCHASING_STATES,
)
from app.services.independent_seed_service import seed_independent_purchasing
from app.services.notification_service import emit_notification
from app.services.workflow_engine import WorkflowError, advance_workflow, start_workflow


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Role(code="SYSTEM_ADMIN", name="System Administrator", is_system_role=True),
                Role(
                    code="INDEPENDENT_ADMIN",
                    name="Independent Administrator",
                    workflow_code="INDEPENDENT",
                    is_system_role=True,
                ),
            ]
        )
        session.commit()
        yield session


def start_independent(db: Session, entity_id: str = "IND-1001") -> WorkflowInstance:
    return start_workflow(
        db,
        FlowStartRequest(
            workflow_code="IND_PURCHASING",
            entity_type="purchase_request",
            entity_id=entity_id,
            context={"store_number": "1001", "region_code": "SOUTHEAST"},
        ),
        actor="independent@example.com",
    )


HAPPY_PATH = (
    ("submit_for_store_review", "workflow.ind.submit"),
    ("store_approve", "workflow.ind.review"),
    ("franchise_approve", "workflow.ind.franchise_approve"),
    ("select_vendor", "workflow.ind.vendor_select"),
    ("verify_pricing", "workflow.ind.review"),
    ("regional_approve", "workflow.ind.regional_approve"),
    ("generate_po", "workflow.ind.review"),
    ("submit_to_vendor", "workflow.ind.review"),
    ("acknowledge_vendor", "workflow.ind.receive"),
    ("schedule_shipment", "workflow.ind.receive"),
    ("receive_order", "workflow.ind.receive"),
)


def complete_independent(db: Session, instance: WorkflowInstance) -> WorkflowInstance:
    for action, permission in HAPPY_PATH:
        instance = advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action=action, actor="independent@example.com"),
            permission_codes={permission},
        )
    return instance


def approval_input(amount: str, **context: object) -> ApprovalPolicyInput:
    return ApprovalPolicyInput(
        workflow_code="IND_PURCHASING",
        entity_type="purchase_request",
        entity_id="IND-1001",
        request_amount=Decimal(amount),
        region_code="SOUTHEAST",
        store_number="1001",
        submitted_by="independent@example.com",
        context=context,
    )


def test_independent_workflow_registration_and_contract() -> None:
    registration = WORKFLOW_REGISTRY.require_active("IND_PURCHASING")

    assert registration.name == "Independent Purchasing"
    assert registration.category == "Independent Ordering"
    assert registration.configuration_namespace == "workflow.ind_purchasing"
    assert registration.lifecycle == WorkflowLifecycle.TESTING
    assert tuple(INDEPENDENT_PURCHASING_DEFINITION.states) == INDEPENDENT_PURCHASING_STATES


def test_independent_seed_installs_every_artifact_idempotently(db: Session) -> None:
    first = seed_independent_purchasing(db, actor="admin@example.com")
    second = seed_independent_purchasing(db, actor="admin@example.com")

    assert first == second
    assert db.scalar(select(func.count()).select_from(WorkflowDefinition)) == 1
    assert (
        db.scalar(select(func.count()).select_from(Permission))
        == len(INDEPENDENT_PERMISSION_DEFINITIONS) + 2
    )
    assert db.scalar(select(func.count()).select_from(ConfigurationEntry)) == (
        len(INDEPENDENT_CONFIGURATION_DEFAULTS) + len(INDEPENDENT_APPROVAL_DEFAULTS)
    )
    assert db.scalar(select(func.count()).select_from(NotificationTemplate)) == len(
        INDEPENDENT_NOTIFICATION_TEMPLATES
    )


def test_independent_workflow_executes_to_completed(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")

    instance = complete_independent(db, start_independent(db))

    assert instance.current_state == "completed"
    assert instance.status == "complete"


def test_independent_approval_policies_and_configuration_override(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")

    store_result = evaluate_approval_policy(db, approval_input("100"))
    regional_result = evaluate_approval_policy(db, approval_input("30000"))
    threshold = db.scalar(
        select(ConfigurationEntry).where(
            ConfigurationEntry.scope_key == "IND_PURCHASING",
            ConfigurationEntry.key == "approval.regional_threshold",
        )
    )
    assert threshold is not None
    threshold.value = {
        "amount": 50,
        "approval_level": "regional",
        "required_permission": "workflow.ind.regional_approve",
    }
    db.commit()
    overridden_result = evaluate_approval_policy(db, approval_input("100"))

    assert store_result.approval_level == ApprovalLevel.STORE
    assert regional_result.approval_level == ApprovalLevel.REGIONAL
    assert overridden_result.approval_level == ApprovalLevel.REGIONAL


def test_independent_notification_uses_shared_framework(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")

    events = emit_notification(
        db,
        NotificationEmitInput(
            workflow_code="IND_PURCHASING",
            event_type="ind.submitted",
            entity_type="purchase_request",
            entity_id="IND-1001",
            actor="independent@example.com",
        ),
    )

    assert len(events) == 1
    assert events[0].status == NotificationStatus.QUEUED
    assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 1


def test_independent_permissions_invalid_transition_and_completed_lock(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")
    instance = start_independent(db)

    with pytest.raises(PermissionError, match="workflow.ind.submit"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action="submit_for_store_review", actor="actor@example.com"),
            permission_codes=set(),
        )
    with pytest.raises(WorkflowError, match="not valid"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action="receive_order", actor="actor@example.com"),
            permission_codes={"workflow.ind.receive"},
        )

    completed = complete_independent(db, instance)
    with pytest.raises(WorkflowError, match="not active"):
        advance_workflow(
            db,
            completed.id,
            FlowActionRequest(action="receive_order", actor="actor@example.com"),
            permission_codes={"workflow.ind.receive"},
        )


def test_independent_administrative_reopen_and_snapshots(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")
    instance = start_independent(db, "IND-REOPEN")
    instance = advance_workflow(
        db,
        instance.id,
        FlowActionRequest(action="cancel", actor="independent@example.com"),
        permission_codes={"workflow.ind.cancel"},
    )

    reopened = advance_workflow(
        db,
        instance.id,
        FlowActionRequest(action="administrative_reopen", actor="admin@example.com"),
        permission_codes={"system.admin"},
    )
    snapshots = db.scalar(
        select(func.count())
        .select_from(EventSnapshot)
        .where(EventSnapshot.entity_id == "IND-REOPEN")
    )

    assert reopened.current_state == "draft"
    assert reopened.status == "active"
    assert snapshots == 3


def test_bpp_workflow_remains_unaffected_by_independent_seed(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")
    seed_bpp_purchasing(db, actor="admin@example.com")

    bpp = db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.code == "BPP_PURCHASING"))
    independent = db.scalar(
        select(WorkflowDefinition).where(WorkflowDefinition.code == "IND_PURCHASING")
    )

    assert bpp is not None and independent is not None
    assert bpp.initial_state == independent.initial_state == "draft"
    assert bpp.transitions != independent.transitions


def test_independent_api_start_enforces_store_authority_and_region(db: Session) -> None:
    seed_independent_purchasing(db, actor="admin@example.com")
    role = db.scalar(select(Role).where(Role.code == "INDEPENDENT_ADMIN"))
    assert role is not None
    user = User(
        email="independent@example.com",
        display_name="Independent User",
        password_hash="not-used",
        region_code="SOUTHEAST",
        is_active=True,
        roles=[role],
    )
    db.add_all(
        [
            user,
            Store(
                store_number="1001",
                name="Independent Store",
                region_code="SOUTHEAST",
                is_active=True,
                is_ordering_enabled=True,
            ),
        ]
    )
    db.commit()

    instance = start_instance(
        FlowStartRequest(
            workflow_code="IND_PURCHASING",
            entity_type="purchase_request",
            entity_id="IND-API-1001",
            context={"store_number": "1001"},
        ),
        db,
        user,
    )

    assert instance.current_state == "draft"
    assert instance.started_by == "independent@example.com"
