from app.schemas.flow import FlowDefinitionResponse, FlowDefinitionWrite, FlowRule


def test_flow_definition_response_contains_rules() -> None:
    rule = FlowRule(action="submit", source="draft", target="submitted")
    response = FlowDefinitionResponse(
        id=1,
        code="TEST",
        name="Test",
        version=1,
        initial_state="draft",
        terminal_states=["complete"],
        rules=[rule],
        is_active=True,
        created_at="2026-06-26T00:00:00Z",
        updated_at="2026-06-26T00:00:00Z",
    )

    assert response.rules[0].target == "submitted"


def test_flow_definition_write_uses_independent_lists() -> None:
    first = FlowDefinitionWrite(code="ONE", name="One", initial_state="draft", rules=[])
    second = FlowDefinitionWrite(code="TWO", name="Two", initial_state="draft", rules=[])

    first.terminal_states.append("complete")

    assert second.terminal_states == []
