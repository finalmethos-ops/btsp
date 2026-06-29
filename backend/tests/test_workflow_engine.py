import pytest

from app.models.workflow import WorkflowDefinition
from app.services.workflow_engine import WorkflowError, ensure_registered_workflow, find_rule


def test_find_rule_matches_current_state_and_action() -> None:
    definition = WorkflowDefinition(
        code="TEST",
        name="Test Flow",
        version=1,
        initial_state="draft",
        terminal_states=["complete"],
        transitions=[{"action": "submit", "source": "draft", "target": "submitted"}],
        is_active=True,
    )

    rule = find_rule(definition, current_state="draft", action="submit")

    assert rule is not None
    assert rule["target"] == "submitted"


def test_find_rule_rejects_invalid_action() -> None:
    definition = WorkflowDefinition(
        code="TEST",
        name="Test Flow",
        version=1,
        initial_state="draft",
        terminal_states=["complete"],
        transitions=[{"action": "submit", "source": "draft", "target": "submitted"}],
        is_active=True,
    )

    assert find_rule(definition, current_state="draft", action="approve") is None


def test_engine_accepts_registered_workflow_code() -> None:
    ensure_registered_workflow("BPP")


def test_engine_rejects_unregistered_workflow_code() -> None:
    with pytest.raises(WorkflowError, match="Workflow is not registered: UNKNOWN"):
        ensure_registered_workflow("UNKNOWN")
