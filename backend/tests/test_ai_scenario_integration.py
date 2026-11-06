"""Cross-boundary AI business scenarios for the 4.23.12 acceptance gate."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai_assistant.audit import AIAuditEvent
from app.ai_assistant.business_rules import (
    AIBusinessRuleRequest,
    AIBusinessRulesPolicy,
)
from app.ai_assistant.contracts import AIActionKind, AIRequest, AIResponseType
from app.ai_assistant.execution import AIAuditedActionExecutor
from app.ai_assistant.failure import AIFailureHandler
from app.ai_assistant.global_search import AISearchContext, resolve_ai_entity
from app.ai_assistant.orchestrator import AIOrchestrator
from app.ai_assistant.rbac import AIToolRBACPolicy
from app.ai_assistant.registry import AIToolDefinition, AIToolRegistry, get_default_ai_tool_registry
from app.ai_assistant.safety import canonical_payload_hash


class FakeSession:
    """Small transaction spy matching the existing audit persistence boundary."""

    def __init__(self):
        self.items = []
        self.flush_count = 0
        self.commit_count = 0
        self.close_count = 0

    def add(self, instance):
        self.items.append(instance)

    def flush(self):
        self.flush_count += 1

    def commit(self):
        self.commit_count += 1

    def close(self):
        self.close_count += 1


class FakeRuleEvaluator:
    def __init__(self, *, allowed: bool):
        self.allowed = allowed
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            allowed=self.allowed,
            evaluations=[
                SimpleNamespace(
                    blocked=not self.allowed,
                    reasons=("A required approval is missing.",) if not self.allowed else (),
                )
            ],
        )


def build_registry():
    return AIToolRegistry(
        (
            AIToolDefinition(
                name="create_task",
                purpose="Create a task after confirmation.",
                action_kind=AIActionKind.WRITE,
                required_permission="tasks.create",
                allowed_entities=("task",),
                requires_confirmation=True,
                input_schema={
                    "type": "object",
                    "required": ["title"],
                    "properties": {"title": {"type": "string", "minLength": 1}},
                    "additionalProperties": False,
                },
            ),
            AIToolDefinition(
                name="get_tasks",
                purpose="Read permitted tasks.",
                action_kind=AIActionKind.READ,
                required_permission="tasks.view",
                allowed_entities=("task",),
                requires_confirmation=False,
                input_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "additionalProperties": False,
                },
            ),
        )
    )


def build_user(company_id, *permissions):
    return SimpleNamespace(
        id=uuid4(),
        company_id=company_id,
        roles=[
            SimpleNamespace(
                permissions=[SimpleNamespace(code=permission) for permission in permissions]
            )
        ],
    )


def build_rule_request(user_id):
    return AIBusinessRuleRequest(
        trigger_event="ai.task.create",
        applies_to="task",
        action="create",
        context={"title": "Prepare proposal"},
        user_id=user_id,
        role_names=("Founder",),
    )


def build_audit_event(request, user, payload, *, permission_decision, rule_decision):
    return AIAuditEvent(
        user_id=user.id,
        company_id=user.company_id,
        request_id=request.request_id,
        user_request=request.message,
        normalized_intent="create_task",
        tool_name="create_task",
        action_metadata={"title": payload.get("title", "unknown")},
        action_payload_hash=canonical_payload_hash(payload),
        permission_decision=permission_decision,
        business_rule_decision=rule_decision,
        confirmation_state="confirmed",
    )


def build_write_context(orchestrator, request, payload, user, *, rules_allowed=True):
    tool = orchestrator.registry.require("create_task")
    authorization = AIToolRBACPolicy().authorize_user(tool, user)
    evaluator = FakeRuleEvaluator(allowed=rules_allowed)
    rule_decision = AIBusinessRulesPolicy().evaluate(
        build_rule_request(user.id), evaluator
    )
    event = build_audit_event(
        request,
        user,
        payload,
        permission_decision=authorization.reason_code,
        rule_decision=rule_decision.reason_code,
    )
    preview = orchestrator.preview_write_action(request, "create_task", payload)
    ticket = orchestrator.issue_write_confirmation(preview)
    return authorization, rule_decision, event, ticket.confirmation_id, evaluator


def test_read_scenario_executes_only_registered_read_tool():
    calls = []

    def read_handler(*, request, context):
        calls.append((request, context))
        return {"items": [{"id": "task-1", "status": context["status"]}]}

    # The registered handler is supplied when the immutable tool definition is created.
    registry = AIToolRegistry(
        (
            AIToolDefinition(
                name="get_tasks",
                purpose="Read permitted tasks.",
                action_kind=AIActionKind.READ,
                required_permission="tasks.view",
                allowed_entities=("task",),
                requires_confirmation=False,
                input_schema={"type": "object", "properties": {"status": {"type": "string"}}, "additionalProperties": False},
                handler=read_handler,
            ),
        )
    )
    request = AIRequest(message="Show overdue tasks", context={"status": "overdue"})
    result = AIOrchestrator(registry).execute_read(request, "get_tasks")

    assert result == {"items": [{"id": "task-1", "status": "overdue"}]}
    assert len(calls) == 1
    assert calls[0][0].request_id == request.request_id


def test_global_search_scenario_preserves_authenticated_company_and_user_scope():
    company_id = uuid4()
    user = build_user(company_id, "global_search.view")
    tool = get_default_ai_tool_registry().require("global_search")
    decision = AIToolRBACPolicy().authorize_user(tool, user)
    assert decision.allowed is True

    calls = []

    def search(**kwargs):
        calls.append(kwargs)
        return {
            "results": [
                {
                    "type": "project",
                    "id": str(uuid4()),
                    "title": "Saru POS",
                    "subtitle": "Active project",
                    "status": "active",
                }
            ]
        }

    resolved = resolve_ai_entity(
        search,
        " Saru POS ",
        AISearchContext(
            user_id=user.id,
            company_id=user.company_id,
            permission_codes=frozenset({"global_search.view"}),
        ),
        entity_type="project",
    )

    assert resolved.resolved is True
    assert resolved.result is not None
    assert resolved.result.title == "Saru POS"
    assert calls[0]["company_id"] == company_id
    assert calls[0]["user_id"] == user.id
    assert calls[0]["entity_type"] == "project"


def test_founder_write_scenario_confirms_authorizes_checks_rules_and_audits():
    registry = build_registry()
    session = FakeSession()
    failure_session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session,
            failure_audit_session_factory=lambda: failure_session,
        ),
    )
    request = AIRequest(message="Create a task named Prepare proposal")
    payload = {"title": "Prepare proposal"}
    company_id = uuid4()
    user = build_user(company_id, "tasks.create")
    authorization, rule_decision, event, ticket_id, evaluator = build_write_context(
        orchestrator, request, payload, user
    )
    created = []

    def domain_handler(*, request, context, payload):
        record = {"id": str(uuid4()), **payload}
        created.append(record)
        return {"record_id": record["id"]}

    result = orchestrator.execute_write(
        request,
        "create_task",
        payload,
        confirmation_id=ticket_id,
        authorization_decision=authorization,
        business_rule_decision=rule_decision,
        audit_event=event,
        handler=domain_handler,
    )

    assert result["record_id"] == created[0]["id"]
    assert len(created) == 1
    assert len(evaluator.requests) == 1
    assert session.flush_count == 1
    assert len(session.items) == 1
    details = json.loads(session.items[0].details)
    assert details["execution_result"] == "success"
    assert details["resulting_record_ids"] == [created[0]["id"]]
    assert details["permission_decision"] == "allowed"
    assert details["business_rule_decision"] == "allowed"
    assert details["confirmation_state"] == "confirmed"


def test_write_scenario_denies_missing_permission_without_domain_mutation():
    registry = build_registry()
    session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session, failure_audit_session_factory=FakeSession
        ),
    )
    request = AIRequest(message="Create a task")
    payload = {"title": "Restricted task"}
    user = build_user(uuid4(), "tasks.view")
    authorization, rule_decision, event, ticket_id, _ = build_write_context(
        orchestrator, request, payload, user
    )
    called = []

    with pytest.raises(PermissionError, match="approved action decisions"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            confirmation_id=ticket_id,
            authorization_decision=authorization,
            business_rule_decision=rule_decision,
            audit_event=event,
            handler=lambda **kwargs: called.append(kwargs),
        )

    assert authorization.allowed is False
    assert called == []
    assert session.items == []


def test_write_scenario_business_rule_block_prevents_mutation_after_confirmation():
    registry = build_registry()
    session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session, failure_audit_session_factory=FakeSession
        ),
    )
    request = AIRequest(message="Create a task")
    payload = {"title": "Task awaiting approval"}
    user = build_user(uuid4(), "tasks.create")
    authorization, rule_decision, event, ticket_id, evaluator = build_write_context(
        orchestrator, request, payload, user, rules_allowed=False
    )
    called = []

    with pytest.raises(PermissionError, match="approved action decisions"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            confirmation_id=ticket_id,
            authorization_decision=authorization,
            business_rule_decision=rule_decision,
            audit_event=event,
            handler=lambda **kwargs: called.append(kwargs),
        )

    assert evaluator.requests
    assert rule_decision.blocked is True
    assert called == []
    assert session.items == []


def test_invalid_tool_input_is_rejected_before_domain_mutation():
    registry = build_registry()
    session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session, failure_audit_session_factory=FakeSession
        ),
    )
    request = AIRequest(message="Create a task")
    payload = {"unexpected": "field"}
    user = build_user(uuid4(), "tasks.create")
    tool = registry.require("create_task")
    authorization = AIToolRBACPolicy().authorize_user(tool, user)
    rule_decision = AIBusinessRulesPolicy().evaluate(
        build_rule_request(user.id), FakeRuleEvaluator(allowed=True)
    )
    event = build_audit_event(
        request,
        user,
        payload,
        permission_decision=authorization.reason_code,
        rule_decision=rule_decision.reason_code,
    )
    called = []

    with pytest.raises(ValueError, match="Missing required tool fields"):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            confirmation_id=None,
            authorization_decision=authorization,
            business_rule_decision=rule_decision,
            audit_event=event,
            handler=lambda **kwargs: called.append(kwargs),
        )

    assert called == []
    assert session.items == []


def test_domain_api_failure_is_audited_and_does_not_claim_action_success():
    registry = build_registry()
    session = FakeSession()
    failure_session = FakeSession()
    orchestrator = AIOrchestrator(
        registry,
        action_executor=AIAuditedActionExecutor(
            session,
            failure_audit_session_factory=lambda: failure_session,
        ),
    )
    request = AIRequest(message="Create a task")
    payload = {"title": "API failure task"}
    user = build_user(uuid4(), "tasks.create")
    authorization, rule_decision, event, ticket_id, _ = build_write_context(
        orchestrator, request, payload, user
    )

    def failed_domain_handler(**kwargs):
        raise TimeoutError("internal endpoint and credentials must not be exposed")

    with pytest.raises(TimeoutError):
        orchestrator.execute_write(
            request,
            "create_task",
            payload,
            confirmation_id=ticket_id,
            authorization_decision=authorization,
            business_rule_decision=rule_decision,
            audit_event=event,
            handler=failed_domain_handler,
        )

    assert session.items == []
    assert len(failure_session.items) == 1
    failure_details = failure_session.items[0].details
    failure_audit = json.loads(failure_details)
    assert failure_audit["execution_result"] == "failed"
    assert failure_audit["failure_error"] == "TimeoutError"
    assert "credentials" not in failure_details

    response = AIFailureHandler.os_api_failure(
        request.request_id,
        "The task service timed out; completion is not confirmed.",
        intent="create_task",
        retryable=False,
        audit_reference="audit-api-timeout",
    )
    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "os_api_failure"
    assert "not confirmed as successful" in response.warnings[0]


def test_partial_write_failure_is_reported_without_automatic_retry():
    response = AIFailureHandler.partial_execution_failure(
        uuid4(),
        "Two task updates succeeded; one failed.",
        intent="bulk_task_update",
        successful_actions=["task-1", "task-2"],
        failed_actions=["task-3"],
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.data["partial"] is True
    assert response.data["successful_actions"] == ["task-1", "task-2"]
    assert response.data["failed_actions"] == ["task-3"]
    assert response.data["retryable"] is False


def test_ai_provider_failure_keeps_non_ai_os_path_available():
    response = AIFailureHandler.ai_provider_failure(uuid4())

    assert response.response_type is AIResponseType.ERROR
    assert response.data["core_os_available"] is True
    assert response.data["retryable"] is True
    assert any("remain available" in warning for warning in response.warnings)
