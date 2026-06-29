import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot  # noqa: F401
from app.models.identity import Permission, Role
from app.models.store import Store  # noqa: F401
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.flow import FlowActionRequest, FlowStartRequest
from app.services.approval_policy_defaults import APPROVAL_PERMISSION_DEFINITIONS
from app.services.bpp_purchasing import (
    BPP_PERMISSION_DEFINITIONS,
    BPP_PURCHASING_CONFIGURATION_DEFAULTS,
    BPP_PURCHASING_DEFINITION,
    BPP_PURCHASING_STATES,
    BPP_PURCHASING_TERMINAL_STATES,
)
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.notification_defaults import BPP_NOTIFICATION_PERMISSION_DEFINITIONS
from app.services.workflow_engine import (
    WorkflowError,
    advance_workflow,
    start_workflow,
    upsert_workflow_definition,
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


def test_bpp_definition_has_all_required_states() -> None:
    assert tuple(BPP_PURCHASING_DEFINITION.states) == BPP_PURCHASING_STATES


def test_bpp_definition_has_expected_terminal_states() -> None:
    assert tuple(BPP_PURCHASING_DEFINITION.terminal_states) == BPP_PURCHASING_TERMINAL_STATES


def test_bpp_definition_has_required_transitions_and_permissions() -> None:
    transitions = {
        (rule.action, rule.source, rule.target): rule.permission
        for rule in BPP_PURCHASING_DEFINITION.rules
    }

    assert transitions[("submit_for_department_review", "draft", "department_review")] == (
        "workflow.bpp.submit"
    )
    assert transitions[("return_for_revision", "executive_approval", "revision_requested")] == (
        "workflow.bpp.revise"
    )
    assert transitions[("receive_order", "receiving", "completed")] == "workflow.bpp.receive"
    assert transitions[("expire", "purchasing_review", "expired")] == "workflow.bpp.expire"
    assert {permission for permission in transitions.values() if permission} == (
        set(BPP_PERMISSION_DEFINITIONS)
        - set(APPROVAL_PERMISSION_DEFINITIONS)
        - set(BPP_NOTIFICATION_PERMISSION_DEFINITIONS)
    )


def test_bpp_configuration_defaults_have_required_values() -> None:
    defaults = {entry.key: entry.value for entry in BPP_PURCHASING_CONFIGURATION_DEFAULTS}

    assert defaults == {
        "enabled": {"enabled": True},
        "executive_approval_threshold": {"amount": 50000},
        "auto_approval_enabled": {"enabled": False},
        "allow_revision": {"enabled": True},
        "allow_cancel_from_draft": {"enabled": True},
        "notification_enabled": {"enabled": True},
    }


def test_bpp_seed_is_idempotent(db: Session) -> None:
    first = seed_bpp_purchasing(db, actor="admin@example.com")
    second = seed_bpp_purchasing(db, actor="admin@example.com")

    assert first == second
    assert db.scalar(select(func.count()).select_from(Permission)) == len(
        BPP_PERMISSION_DEFINITIONS
    )
    assert db.scalar(select(func.count()).select_from(WorkflowDefinition)) == 1
    assert db.scalar(select(func.count()).select_from(ConfigurationEntry)) == len(
        BPP_PURCHASING_CONFIGURATION_DEFAULTS
    )
    bpp_role = db.scalar(select(Role).where(Role.code == "BPP_ADMIN"))
    assert bpp_role is not None
    assert {permission.code for permission in bpp_role.permissions}.issuperset(
        BPP_PERMISSION_DEFINITIONS
    )


def _start_seeded_workflow(db: Session) -> WorkflowInstance:
    seed_bpp_purchasing(db, actor="admin@example.com")
    return start_workflow(
        db,
        FlowStartRequest(
            workflow_code="BPP_PURCHASING",
            entity_type="purchase_request",
            entity_id="PR-1001",
        ),
        actor="requester@example.com",
    )


def test_invalid_transition_is_rejected(db: Session) -> None:
    instance = _start_seeded_workflow(db)

    with pytest.raises(WorkflowError, match="not valid for current state"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action="executive_approve", actor="actor@example.com"),
            permission_codes={"workflow.bpp.executive_approve"},
        )


def test_missing_permission_is_rejected(db: Session) -> None:
    instance = _start_seeded_workflow(db)

    with pytest.raises(PermissionError, match="workflow.bpp.submit"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(
                action="submit_for_department_review",
                actor="actor@example.com",
            ),
            permission_codes=set(),
        )


def test_completed_workflow_cannot_advance(db: Session) -> None:
    instance = _start_seeded_workflow(db)
    instance.status = "complete"
    instance.current_state = "completed"
    db.commit()

    with pytest.raises(WorkflowError, match="not active"):
        advance_workflow(
            db,
            instance.id,
            FlowActionRequest(action="receive_order", actor="actor@example.com"),
            permission_codes={"workflow.bpp.receive"},
        )


def test_instance_advances_with_its_recorded_definition_version(db: Session) -> None:
    instance = _start_seeded_workflow(db)
    version_two = BPP_PURCHASING_DEFINITION.model_copy(
        deep=True,
        update={"version": 2, "rules": []},
    )
    upsert_workflow_definition(db, version_two)

    advanced = advance_workflow(
        db,
        instance.id,
        FlowActionRequest(
            action="submit_for_department_review",
            actor="actor@example.com",
        ),
        permission_codes={"workflow.bpp.submit"},
    )

    assert advanced.workflow_version == 1
    assert advanced.current_state == "department_review"
