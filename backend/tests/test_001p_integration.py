from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.workflows import (
    WORKFLOW_REGISTRY,
    WorkflowCode,
    WorkflowRegistration,
    WorkflowRegistry,
)
from app.db.session import Base
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role
from app.models.notification import NotificationEvent, NotificationTemplate  # noqa: F401
from app.models.store import Store  # noqa: F401
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.approval_policy import ApprovalLevel, ApprovalPolicyInput
from app.schemas.flow import FlowActionRequest, FlowStartRequest
from app.schemas.notification import NotificationEmitInput, NotificationStatus
from app.services.approval_policy_service import (
    evaluate_approval_policy,
    seed_bpp_approval_defaults,
)
from app.services.bpp_purchasing import BPP_PERMISSION_DEFINITIONS
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.notification_service import (
    emit_notification,
    seed_bpp_notification_defaults,
)
from app.services.workflow_engine import (
    WorkflowError,
    advance_workflow,
    ensure_registered_workflow,
    start_workflow,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Role(code="SYSTEM_ADMIN", name="System Administrator", is_system_role=True),
                Role(
                    code="BPP_ADMIN",
                    name="BPP Administrator",
                    workflow_code="BPP",
                    is_system_role=True,
                ),
            ]
        )
        session.commit()
        yield session


def seed_001p(db: Session) -> None:
    seed_bpp_purchasing(db, actor="admin@example.com")
    seed_bpp_approval_defaults(db, actor="admin@example.com")
    seed_bpp_notification_defaults(db, actor="admin@example.com")


def start_bpp(db: Session, entity_id: str = "PR-E2E-001") -> WorkflowInstance:
    return start_workflow(
        db,
        FlowStartRequest(
            workflow_code="BPP_PURCHASING",
            entity_type="purchase_request",
            entity_id=entity_id,
            context={"request_amount": 75000},
        ),
        actor="admin@example.com",
    )


HAPPY_PATH_ACTIONS = (
    ("submit_for_department_review", "workflow.bpp.submit"),
    ("department_approve", "workflow.bpp.department_review"),
    ("purchasing_approve", "workflow.bpp.purchasing_review"),
    ("select_vendor", "workflow.bpp.vendor_select"),
    ("verify_cost", "workflow.bpp.cost_verify"),
    ("executive_approve", "workflow.bpp.executive_approve"),
    ("generate_po", "workflow.bpp.po_generate"),
    ("submit_to_vendor", "workflow.bpp.vendor_submit"),
    ("confirm_vendor", "workflow.bpp.vendor_confirm"),
    ("schedule_shipment", "workflow.bpp.shipment_schedule"),
    ("receive_order", "workflow.bpp.receive"),
)


def complete_bpp(db: Session, instance: WorkflowInstance) -> WorkflowInstance:
    for action, permission in HAPPY_PATH_ACTIONS:
        instance = advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action=action, actor="admin@example.com"),
            permission_codes={permission},
        )
    return instance


def test_bpp_seed_installs_registry_definition_config_permissions(db: Session) -> None:
    seed_001p(db)

    registration = WORKFLOW_REGISTRY.require_active(WorkflowCode.BPP_PURCHASING)
    definition = db.scalar(
        select(WorkflowDefinition).where(WorkflowDefinition.code == registration.code)
    )
    config_count = db.scalar(
        select(func.count())
        .select_from(ConfigurationEntry)
        .where(ConfigurationEntry.scope_key == "BPP_PURCHASING")
    )
    permission_codes = set(db.scalars(select(Permission.code)).all())

    assert definition is not None
    assert definition.version == 1
    assert config_count == 17
    assert permission_codes.issuperset(BPP_PERMISSION_DEFINITIONS)


def test_bpp_workflow_happy_path_completes(db: Session) -> None:
    seed_001p(db)

    instance = complete_bpp(db, start_bpp(db))

    assert instance.current_state == "completed"
    assert instance.status == "complete"


def test_bpp_invalid_transition_rejected(db: Session) -> None:
    seed_001p(db)
    instance = start_bpp(db)

    with pytest.raises(WorkflowError, match="not valid for current state"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action="receive_order", actor="admin@example.com"),
            permission_codes={"workflow.bpp.receive"},
        )


def test_bpp_missing_permission_rejected(db: Session) -> None:
    seed_001p(db)
    instance = start_bpp(db)

    with pytest.raises(PermissionError, match="workflow.bpp.submit"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(
                action="submit_for_department_review",
                actor="admin@example.com",
            ),
            permission_codes=set(),
        )


def test_bpp_approval_policy_executive_threshold(db: Session) -> None:
    seed_001p(db)

    result = evaluate_approval_policy(
        db,
        ApprovalPolicyInput(
            workflow_code="BPP_PURCHASING",
            entity_type="purchase_request",
            entity_id="PR-E2E-001",
            request_amount=Decimal("50000"),
            submitted_by="admin@example.com",
        ),
    )

    assert result.approval_level == ApprovalLevel.EXECUTIVE
    assert result.required_permission == "workflow.bpp.executive_approve"


def test_bpp_notification_emit_creates_event(db: Session) -> None:
    seed_001p(db)

    events = emit_notification(
        db,
        NotificationEmitInput(
            workflow_code="BPP_PURCHASING",
            event_type="bpp.submitted",
            entity_type="purchase_request",
            entity_id="PR-E2E-001",
            actor="admin@example.com",
        ),
    )

    assert len(events) == 1
    assert events[0].status == NotificationStatus.QUEUED
    assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 1


def test_bpp_snapshots_written_for_workflow_events(db: Session) -> None:
    seed_001p(db)
    complete_bpp(db, start_bpp(db))

    workflow_snapshot_count = db.scalar(
        select(func.count())
        .select_from(EventSnapshot)
        .where(EventSnapshot.event_type.in_(["workflow.started", "workflow.advanced"]))
    )

    assert workflow_snapshot_count == 12


def test_bpp_registry_entry_matches_active_definition(db: Session) -> None:
    seed_001p(db)

    registration = WORKFLOW_REGISTRY.require_active("BPP_PURCHASING")
    definition = db.scalar(
        select(WorkflowDefinition).where(
            WorkflowDefinition.code == registration.code,
            WorkflowDefinition.is_active.is_(True),
        )
    )

    assert definition is not None
    assert definition.name == registration.name
    assert definition.business_area == registration.business_area
    assert definition.configuration_namespace == registration.configuration_namespace


def test_inactive_workflow_registry_entry_cannot_be_used(monkeypatch: pytest.MonkeyPatch) -> None:
    inactive_registry = WorkflowRegistry(
        [
            WorkflowRegistration(
                code=WorkflowCode.BPP_PURCHASING,
                name="BPP Purchasing",
                route="/workflows/bpp",
                permission_code="workflow.bpp.submit",
                is_active=False,
            )
        ]
    )
    monkeypatch.setattr(
        "app.services.workflow_engine.WORKFLOW_REGISTRY",
        inactive_registry,
    )

    with pytest.raises(WorkflowError, match="Workflow is not active"):
        ensure_registered_workflow("BPP_PURCHASING")
