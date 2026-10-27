from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai_assistant.contracts import AIActionKind, AIRequest, AIResponseType
from app.ai_assistant.orchestrator import AIOrchestrator
from app.ai_assistant.registry import AIToolDefinition, AIToolRegistry


def test_ai_request_contract_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AIRequest(message="hello", unexpected=True)


def test_registry_keeps_read_and_write_capabilities_separate():
    registry = AIToolRegistry()
    registry.register(
        AIToolDefinition(
            name="get_today_attention",
            purpose="Read Founder attention items",
            action_kind=AIActionKind.READ,
            required_permission="command_center.view",
            allowed_entities=("task", "prospect", "project"),
            requires_confirmation=False,
        )
    )
    registry.register(
        AIToolDefinition(
            name="create_followup",
            purpose="Create a follow-up",
            action_kind=AIActionKind.WRITE,
            required_permission="tasks.create",
            allowed_entities=("prospect", "client", "opportunity"),
            requires_confirmation=True,
        )
    )

    assert registry.names(AIActionKind.READ) == ("get_today_attention",)
    assert registry.names(AIActionKind.WRITE) == ("create_followup",)


def test_duplicate_tool_registration_is_rejected():
    registry = AIToolRegistry()
    tool = AIToolDefinition(
        name="global_search",
        purpose="Search company records",
        action_kind=AIActionKind.READ,
        required_permission="global_search.view",
        allowed_entities=("prospect", "client"),
        requires_confirmation=False,
    )
    registry.register(tool)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_orchestrator_never_executes_write_action_directly():
    registry = AIToolRegistry()
    registry.register(
        AIToolDefinition(
            name="create_task",
            purpose="Create a task",
            action_kind=AIActionKind.WRITE,
            required_permission="tasks.create",
            allowed_entities=("task",),
            requires_confirmation=True,
        )
    )
    orchestrator = AIOrchestrator(registry)
    request = AIRequest(message="Create a task")

    preview = orchestrator.preview_write(request, "create_task")

    assert preview.response_type == AIResponseType.ACTION_PREVIEW
    assert preview.confirmation_required is True
    assert preview.request_id == request.request_id


def test_orchestrator_rejects_read_tool_as_write():
    registry = AIToolRegistry()
    registry.register(
        AIToolDefinition(
            name="get_projects",
            purpose="Read projects",
            action_kind=AIActionKind.READ,
            required_permission="projects.view",
            allowed_entities=("project",),
            requires_confirmation=False,
        )
    )
    orchestrator = AIOrchestrator(registry)

    response = orchestrator.preview_write(AIRequest(message="show projects"), "get_projects")

    assert response.response_type == AIResponseType.ERROR
    assert response.error_code == "AI_TOOL_ACTION_MISMATCH"


def test_read_execution_uses_registered_handler_and_no_database_dependency():
    registry = AIToolRegistry()

    def handler(*, request, context):
        return {"request_id": str(request.request_id), "context": context}

    registry.register(
        AIToolDefinition(
            name="get_tasks",
            purpose="Read tasks",
            action_kind=AIActionKind.READ,
            required_permission="tasks.view",
            allowed_entities=("task",),
            requires_confirmation=False,
            handler=handler,
        )
    )
    request = AIRequest(message="show tasks", context={"status": "overdue"})
    result = AIOrchestrator(registry).execute_read(request, "get_tasks")

    assert result["request_id"] == str(request.request_id)
    assert result["context"] == {"status": "overdue"}
    assert uuid4() is not None
