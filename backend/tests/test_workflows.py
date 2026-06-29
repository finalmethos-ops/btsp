import pytest

from app.core.workflows import (
    WORKFLOW_REGISTRY,
    WORKFLOW_ROUTES,
    WorkflowCode,
    WorkflowRegistration,
    WorkflowRegistry,
    WorkflowRegistryError,
)


def test_workflow_registry_keeps_workflows_separate() -> None:
    bpp = WORKFLOW_REGISTRY.require(WorkflowCode.BPP)
    independent = WORKFLOW_REGISTRY.require(WorkflowCode.INDEPENDENT)

    assert bpp.route == "/workflows/bpp"
    assert independent.route == "/workflows/independent"
    assert bpp.route != independent.route
    assert bpp.permission_code != independent.permission_code
    assert WORKFLOW_ROUTES[WorkflowCode.BPP] == bpp.route


def test_workflow_registry_preserves_registration_order() -> None:
    assert [entry.code for entry in WORKFLOW_REGISTRY.list()] == [
        WorkflowCode.BPP,
        WorkflowCode.BPP_PURCHASING,
        WorkflowCode.INDEPENDENT,
        WorkflowCode.IND_PURCHASING,
    ]


def test_workflow_registry_rejects_duplicate_codes() -> None:
    registration = WorkflowRegistration(
        code=WorkflowCode.BPP,
        name="BPP Ordering",
        route="/workflows/bpp",
        permission_code="orders.bpp.manage",
    )

    with pytest.raises(WorkflowRegistryError, match="Duplicate workflow registration"):
        WorkflowRegistry([registration, registration])


def test_workflow_registry_rejects_unknown_code() -> None:
    with pytest.raises(WorkflowRegistryError, match="Workflow is not registered: UNKNOWN"):
        WORKFLOW_REGISTRY.require("UNKNOWN")
