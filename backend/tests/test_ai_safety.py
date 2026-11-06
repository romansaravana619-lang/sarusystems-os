from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
from uuid import uuid4

import pytest

from app.ai_assistant import AIActionKind, AIRequest, get_default_ai_tool_registry
from app.ai_assistant.registry import AIToolDefinition
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

    replay = policy.authorize_write_execution(
        request, "create_task", payload, ticket.confirmation_id, now=issued_at + timedelta(seconds=2)
    )
    assert replay.allowed is False
    assert replay.reason == "confirmation_already_used"


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


def test_confirmation_is_bound_to_request_and_tool() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    preview = policy.preview_write(request, "create_task", {"title": "Follow up"})
    ticket = policy.issue_confirmation(preview)

    other_request = make_request()
    mismatch = policy.confirm_write(
        other_request, "create_task", {"title": "Follow up"}, ticket.confirmation_id
    )
    assert mismatch.allowed is False
    assert mismatch.reason == "confirmation_context_mismatch"

    task_id = str(uuid4())
    other_tool = policy.confirm_write(
        request,
        "update_task",
        {"task_id": task_id, "field": "priority", "value": "high"},
        ticket.confirmation_id,
    )
    assert other_tool.allowed is False
    assert other_tool.reason == "confirmation_context_mismatch"


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


def test_preview_must_be_issued_by_the_same_policy_and_only_once() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    preview = policy.preview_write(make_request(), "create_task", {"title": "Follow up"})

    with pytest.raises(PermissionError, match="created by this policy"):
        policy.issue_confirmation(replace(preview, summary="tampered"))

    policy.issue_confirmation(preview)
    with pytest.raises(PermissionError, match="created by this policy"):
        policy.issue_confirmation(preview)


def test_payload_schema_validates_types_and_uuid_formats() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())

    with pytest.raises(ValueError, match="schema type string"):
        policy.preview_write(make_request(), "create_task", {"title": 123})

    with pytest.raises(ValueError, match="valid UUID"):
        policy.preview_write(
            make_request(),
            "create_followup",
            {"target_type": "prospect", "target_id": "not-a-uuid", "title": "Follow up", "due_at": "2026-11-07T10:00:00Z"},
        )


def test_confirmation_ttl_and_timestamps_must_be_valid() -> None:
    registry = get_default_ai_tool_registry()
    with pytest.raises(ValueError, match="TTL"):
        AISafetyPolicy(registry, ttl=timedelta(0))

    policy = AISafetyPolicy(registry)
    preview = policy.preview_write(make_request(), "create_task", {"title": "Follow up"})
    with pytest.raises(ValueError, match="timezone-aware"):
        policy.issue_confirmation(preview, now=datetime(2026, 10, 28, 10, 0))


def test_payload_hash_rejects_non_json_and_non_finite_values() -> None:
    with pytest.raises(ValueError, match="not JSON serializable"):
        canonical_payload_hash({"value": object()})

    with pytest.raises(ValueError, match="finite JSON numbers"):
        canonical_payload_hash({"value": math.nan})


def test_payload_hash_is_independent_of_object_key_order() -> None:
    assert canonical_payload_hash({"title": "Follow up", "priority": "high"}) == canonical_payload_hash(
        {"priority": "high", "title": "Follow up"}
    )


def test_confirmation_consumption_is_atomic_across_threads() -> None:
    policy = AISafetyPolicy(get_default_ai_tool_registry())
    request = make_request()
    payload = {"title": "Follow up"}
    preview = policy.preview_write(request, "create_task", payload)
    ticket = policy.issue_confirmation(preview)

    def consume_confirmation(_: int) -> bool:
        return policy.confirm_write(
            request,
            "create_task",
            payload,
            ticket.confirmation_id,
        ).allowed

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(consume_confirmation, range(12)))

    assert sum(results) == 1


def test_payload_hash_rejects_circular_references() -> None:
    payload = {}
    payload["self"] = payload

    with pytest.raises(ValueError, match="circular reference"):
        canonical_payload_hash(payload)
