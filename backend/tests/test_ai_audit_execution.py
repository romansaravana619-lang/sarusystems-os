import json
from dataclasses import replace
from uuid import uuid4

import pytest

from app.ai_assistant.audit import AIAuditEvent
from app.ai_assistant.business_rules import AIBusinessRuleDecision
from app.ai_assistant.contracts import AIActionKind, AIRequest
from app.ai_assistant.execution import AIAuditedActionExecutor
from app.ai_assistant.orchestrator import AIOrchestrator
from app.ai_assistant.rbac import AIAuthorizationDecision
from app.ai_assistant.registry import AIToolDefinition, AIToolRegistry
from app.ai_assistant.safety import AISafetyPolicy, canonical_payload_hash


class FakeSession:
    def __init__(self) -> None:
        self.items = []
        self.flush_count = 0
        self.commit_count = 0
        self.close_count = 0

    def add(self, instance) -> None:
        self.items.append(instance)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1

    def close(self) -> None:
        self.close_count += 1


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


def build_context(
    request: AIRequest,
    payload: dict,
    *,
    confirmation_state: str = "confirmed",
) -> AIAuditEvent:
    return AIAuditEvent(
        user_id=uuid4(),
        company_id=uuid4(),
        request_id=request.request_id,
        user_request=request.message,
        normalized_intent="create_task",
        tool_name="create_task",
        action_metadata={"title": "Prepare proposal"},
        action_payload_hash=canonical_payload_hash(payload),
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


def approval_context(event: AIAuditEvent):
    authorization = AIAuthorizationDecision(
        allowed=True,
        reason_code="allowed",
        tool_name="create_task",
        required_permission="task.create",
        user_id=event.user_id,
        company_id=event.company_id,
    )
    business_rules = AIBusinessRuleDecision(
        allowed=True,
        reason_code="allowed",
        blocked=False,
        trigger_event="ai.tool.write.create_task",
        applies_to="task",
        action="create",
        evaluation_count=1,
    )
    return authorization, business_rules


def test_orchestrator_executes_confirmed_write_and_persists_success_audit() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    executor = AIAuditedActionExecutor(session, failure_audit_session_factory=FakeSession)
    orchestrator = AIOrchestrator(registry, action_executor=executor)
    record_id = uuid4()
    calls = []

    event = build_context(request, payload)
    authorization, business_rules = approval_context(event)

    def handler(**kwargs):
        calls.append(kwargs)
        return {"record_id": str(record_id)}

    result = orchestrator.execute_write(
        request,
        "create_task",
        payload,
        safety_decision=confirmed_decision(registry, request, payload),
        authorization_decision=authorization,
        business_rule_decision=business_rules,
        audit_event=event,
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
    failure_session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session,
            failure_audit_session_factory=lambda: failure_session,
        ),
    )
    event = build_context(request, payload)
    authorization, business_rules = approval_context(event)

    def handler(**kwargs):
        raise RuntimeError("provider_secret=do-not-store-this")

    with pytest.raises(RuntimeError, match="provider_secret"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            authorization_decision=authorization,
            business_rule_decision=business_rules,
            audit_event=event,
            handler=handler,
        )

    assert session.items == []
    assert failure_session.flush_count == 1
    assert failure_session.commit_count == 1
    assert failure_session.close_count == 1
    details = json.loads(failure_session.items[0].details)
    assert details["execution_result"] == "failed"
    assert details["failure_error"] == "RuntimeError"
    assert "do-not-store-this" not in failure_session.items[0].details


def test_write_is_not_executed_without_valid_consumed_confirmation() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session, failure_audit_session_factory=FakeSession))
    called = False

    event = build_context(request, payload)
    authorization, business_rules = approval_context(event)

    def handler(**kwargs):
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="valid, consumed confirmation"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, {"title": "Different payload"}),
            authorization_decision=authorization,
            business_rule_decision=business_rules,
            audit_event=event,
            handler=handler,
        )

    assert called is False
    assert session.items == []


def test_write_is_not_executed_when_audit_context_does_not_match_request() -> None:
    registry = build_registry()
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    session = FakeSession()
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session, failure_audit_session_factory=FakeSession))
    called = False
    mismatched = build_context(AIRequest(message="Different request"), payload)
    authorization, business_rules = approval_context(mismatched)

    def handler(**kwargs):
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="audit context"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            authorization_decision=authorization,
            business_rule_decision=business_rules,
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
    orchestrator = AIOrchestrator(registry, action_executor=AIAuditedActionExecutor(session, failure_audit_session_factory=FakeSession))
    read_event = build_context(request, payload)
    authorization, business_rules = approval_context(read_event)
    with pytest.raises(PermissionError, match="audit context"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            safety_decision=confirmed_decision(registry, request, payload),
            authorization_decision=authorization,
            business_rule_decision=business_rules,
            audit_event=replace(read_event, read_only=True),
            handler=lambda **kwargs: {"record_id": uuid4()},
        )

    assert session.items == []
