from types import SimpleNamespace

from app.api.v1.routes.workflows import read_available_workflows, read_workflow_registry


def test_available_workflows_returns_only_registered_user_assignments() -> None:
    user = SimpleNamespace(
        roles=[
            SimpleNamespace(workflow_code="BPP"),
            SimpleNamespace(workflow_code="UNKNOWN"),
        ]
    )

    workflows = read_available_workflows(user)  # type: ignore[arg-type]

    assert [workflow.code for workflow in workflows] == ["BPP"]
    assert workflows[0].name == "BPP Ordering"


def test_workflow_registry_route_returns_complete_catalog() -> None:
    workflows = read_workflow_registry(SimpleNamespace())  # type: ignore[arg-type]

    assert [workflow.code for workflow in workflows] == [
        "BPP",
        "BPP_PURCHASING",
        "INDEPENDENT",
        "IND_PURCHASING",
    ]
