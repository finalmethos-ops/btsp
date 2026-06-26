from app.core.workflows import WORKFLOW_ROUTES, WorkflowCode


def test_workflow_routes_are_separate() -> None:
    assert WORKFLOW_ROUTES[WorkflowCode.BPP] == "/workflows/bpp"
    assert WORKFLOW_ROUTES[WorkflowCode.INDEPENDENT] == "/workflows/independent"
    assert WORKFLOW_ROUTES[WorkflowCode.BPP] != WORKFLOW_ROUTES[WorkflowCode.INDEPENDENT]
