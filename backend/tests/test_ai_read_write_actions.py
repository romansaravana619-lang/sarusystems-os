from app.ai_assistant import AIActionKind, get_default_ai_tool_registry
from app.ai_assistant.read_write import AIReadWritePolicy, ensure_read_action, ensure_write_action


def test_read_tools_auto_execute_without_confirmation() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    decision = ensure_read_action(policy, "get_sales_pipeline", {})
    assert decision.allowed is True
    assert decision.confirmation_required is False
    assert decision.action_kind == AIActionKind.READ


def test_write_tools_require_confirmation() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    payload = {"title": "Follow up", "due_date": "2026-10-28"}
    decision = ensure_write_action(policy, "create_task", payload, confirmation_granted=False)
    assert decision.allowed is False
    assert decision.confirmation_required is True
    assert decision.reason == "write_confirmation_required"


def test_write_tools_pass_after_confirmation() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    payload = {"title": "Follow up"}
    decision = ensure_write_action(policy, "create_task", payload, confirmation_granted=True)
    assert decision.allowed is True
    assert decision.confirmation_required is True
    assert decision.reason == "write_confirmation_granted"


def test_read_boundary_rejects_write_tool() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    try:
        ensure_read_action(policy, "create_task", {"title": "x"})
    except PermissionError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("write tool crossed read boundary")


def test_write_boundary_rejects_read_tool() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    try:
        ensure_write_action(policy, "get_tasks", {}, confirmation_granted=True)
    except PermissionError as exc:
        assert "write" in str(exc)
    else:
        raise AssertionError("read tool crossed write boundary")


def test_required_fields_and_unknown_fields_are_validated() -> None:
    policy = AIReadWritePolicy(get_default_ai_tool_registry())
    try:
        ensure_write_action(policy, "create_task", {}, confirmation_granted=True)
    except ValueError as exc:
        assert "title" in str(exc)
    else:
        raise AssertionError("missing required field was accepted")

    try:
        ensure_read_action(policy, "get_sales_pipeline", {"unexpected": True})
    except ValueError as exc:
        assert "Unknown tool fields" in str(exc)
    else:
        raise AssertionError("unknown field was accepted")
