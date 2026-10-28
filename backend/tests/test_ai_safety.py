from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.ai_assistant import AIRequest, get_default_ai_tool_registry
from app.ai_assistant.safety import AISafetyPolicy, canonical_payload_hash


def make_request() -> AIRequest:
    return AIRequest(request_id=uuid4(), message="Create a follow-up task")


def test_write_requires_explicit_confirmation_and_returns_preview() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    payload = {"title": "Follow up"}

    decision = policy.authorize_write_execution(request, "create_task", payload, None)

    assert decision.allowed is False
    assert decision.confirmation_required is True
    assert decision.reason == "explicit_confirmation_required"
    assert decision.preview is not None
    assert decision.preview.tool_name == "create_task"
    assert decision.preview.payload_hash == canonical_payload_hash(payload)


def test_confirmation_is_bound_to_exact_request_tool_and_payload() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    payload = {"title": "Follow up"}
    preview = policy.preview_write(request, "create_task", payload)
    issued_at = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    ticket = policy.issue_confirmation(preview, now=issued_at)

    valid = policy.authorize_write_execution(
        request, "create_task", payload, ticket.confirmation_id, now=issued_at + timedelta(seconds=1)
    )
    assert valid.allowed is True
    assert valid.reason == "confirmation_validated"

    mismatch = policy.authorize_write_execution(
        request, "create_task", {"title": "Changed"}, ticket.confirmation_id, now=issued_at + timedelta(seconds=2)
    )
    assert mismatch.allowed is False
    assert mismatch.reason == "confirmation_already_used"


def test_payload_mismatch_is_rejected_before_consuming_confirmation() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    original = {"title": "Follow up"}
    preview = policy.preview_write(request, "create_task", original)
    issued_at = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    ticket = policy.issue_confirmation(preview, now=issued_at)

    decision = policy.authorize_write_execution(
        request, "create_task", {"title": "Changed"}, ticket.confirmation_id, now=issued_at + timedelta(seconds=1)
    )
    assert decision.allowed is False
    assert decision.reason == "confirmation_payload_mismatch"

    retry = policy.authorize_write_execution(
        request, "create_task", original, ticket.confirmation_id, now=issued_at + timedelta(seconds=2)
    )
    assert retry.allowed is True


def test_expired_confirmation_is_rejected() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry(), ttl=timedelta(minutes=5))
    request = make_request()
    payload = {"title": "Follow up"}
    preview = policy.preview_write(request, "create_task", payload)
    issued_at = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    ticket = policy.issue_confirmation(preview, now=issued_at)

    decision = policy.authorize_write_execution(
        request, "create_task", payload, ticket.confirmation_id, now=issued_at + timedelta(minutes=5)
    )
    assert decision.allowed is False
    assert decision.reason == "confirmation_expired"


def test_confirmation_is_single_use() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    payload = {"title": "Follow up"}
    preview = policy.preview_write(request, "create_task", payload)
    issued_at = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    ticket = policy.issue_confirmation(preview, now=issued_at)

    first = policy.authorize_write_execution(
        request, "create_task", payload, ticket.confirmation_id, now=issued_at + timedelta(seconds=1)
    )
    second = policy.authorize_write_execution(
        request, "create_task", payload, ticket.confirmation_id, now=issued_at + timedelta(seconds=2)
    )

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "confirmation_already_used"


def test_read_tools_cannot_cross_safety_write_boundary() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    with pytest.raises(PermissionError, match="write tools"):
        policy.preview_write(make_request(), "get_tasks", {})


def test_write_tool_configuration_must_require_confirmation() -> None:
    from app.ai_assistant.registry import AIToolDefinition
    from app.ai_assistant import AIActionKind

    unsafe_tool = AIToolDefinition(
        name="unsafe_write",
        purpose="test",
        action_kind=AIActionKind.WRITE,
        required_permission="test.write",
        allowed_entities=("task",),
        requires_confirmation=False,
    )
    registry = get_default_ai_tool_registry()
    registry.register(unsafe_tool)

    with pytest.raises(PermissionError, match="require explicit confirmation"):
        AISafetyPolicy(registry).preview_write(make_request(), "unsafe_write", {})
