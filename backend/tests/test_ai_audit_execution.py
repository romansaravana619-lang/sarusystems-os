import json
from uuid import uuid4

import pytest

from app.ai_assistant.audit import AIAuditEvent
from app.ai_assistant.contracts import AIActionKind, AIRequest
from app.ai_assistant.execution import AIAuditedActionExecutor
from app.ai_assistant.orchestrator import AIOrchestrator
from app.ai_assistant.registry import AIToolDefinition, AIToolRegistry
from app.ai_assistant.safety import AISafetyPolicy


class FakeSession:
    def __init__(self) -> None:
        self.items = []
        self.flush_count = 0

    def add(self, instance) -> None:
        self.items.append(instance)

    def flush(self) -> None:
        self.flush_count += 1


def build_registry() -> AIToolRegistry:
    tool = AIToolDefinition(
        name="create_task",
        purpose="Create a task after explicit confirmation.",
        action_kind=AIActionKind.WRITE,
        required_permission="task.create",
        allowed_entities=("task",),
        requires_confirmation=True,
        input_schema={
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        },
    )
    return AIToolRegistry((tool,))


def build_context(request: AIRequest, *, confirmation_state: str = "confirmed") -> AIAuditEvent:
    return AIAuditEvent(
        user_id=uuid4(),
        company_id=uuid4(),
        request_id=request.request_id,
        user_request=request.message,
        normalized_intent="create_task",
        tool_name="create_task",
        action_metadata={"title": "Prepare proposal"},
        permission_decision="allowed",
        business_rule_decision="allowed",
        confirmation_state=confirmation_state,
    )


def confirmed_decision(registry, request, payload):
    policy = AISafetyPolicy(registry)
    preview = policy.preview_write(request, "create_task", payload)
    ticket = policy.issue_confirmation(preview)
    decision = policy.confirm_write(request, "create_task", payload, ticket.confirmation_id)
    return decision


def test_orchestrator_executes_confirmed_write_and_persists_success_audit() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    executor = AIAuditedActionExecutor(session)
    orchestrator = AIOrchestrator(registry, action_executor=executor)
    record_id = uuid4()
    calls = []

    def handler(**kwargs):
        calls.append(kwargs)
        return {"record_id": str(record_id)}

    result = orchestrator.execute_write(
        request,
        "create_task",
        payload,
        safety_decision=confirmed_decision(registry, request, payload),
        audit_event=build_context(request),
        handler=handler,
    )

    assert result == {"record_id": str(record_id)}
    assert len(calls) == 1
    assert session.flush_count == 1
    assert len(session.items) == 1
    audit = session.items[0]
    details = json.loads(audit.details)
    assert audit.action == "ai_assistant"
    assert audit.entity_id == str(request.request_id)
    assert details["execution_result"] == "success"
    assert details["resulting_record_ids"] == [str(record_id)]
    assert details["permission_decision"] == "allowed"
    assert details["business_rule_decision"] == "allowed"
    assert details["confirmation_state"] == "confirmed"
    assert details["audit_reference"]


def test_orchestrator_records_sanitized_failure_and_reraises() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(session),
    )

    def handler(**kwargs):
        raise RuntimeError("provider_secret=do-not-store-this")

    with pytest.raises(RuntimeError, match="provider_secret"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            audit_event=build_context(request),
            handler=handler,
        )

    assert session.flush_count == 1
    details = json.loads(session.items[0].details)
    assert details["execution_result"] == "failed"
    assert details["failure_error"] == "RuntimeError"
    assert "do-not-store-this" not in session.items[0].details


def test_write_is_not_executed_without_valid_consumed_confirmation() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session))
    called = False

    def handler(**kwargs):
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="valid, consumed confirmation"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, {"title": "Different payload"}),
            audit_event=build_context(request),
            handler=handler,
        )

    assert called is False
    assert session.items == []


def test_write_is_not_executed_when_audit_context_does_not_match_request() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session))
    called = False
    mismatched = build_context(AIRequest(message="Different request"))

    def handler(**kwargs):
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="audit context"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            audit_event=mismatched,
            handler=handler,
        )

    assert called is False
    assert session.items == []


def test_read_only_event_cannot_be_used_for_write_execution() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session))
    read_event = build_context(request)
    from dataclasses import replace

    with pytest.raises(PermissionError, match="audit context"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            audit_event=replace(read_event, read_only=True),
            handler=lambda **kwargs: {"record_id": uuid4()},
        )

    assert session.items == []
