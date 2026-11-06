from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.ai_assistant import router as ai_router
from app.ai_assistant.contracts import AIResponseType
from app.ai_assistant.router import (
    AIReadInvocation,
    AIWriteConfirmation,
    AIWriteInvocation,
    confirm_ai_write,
    execute_ai_read,
    list_ai_read_tools,
    preview_ai_write,
)
from app.tasks.schemas import TaskResponse


class FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


def user_with_permissions(*codes):
    return SimpleNamespace(
        id=uuid4(),
        company_id=uuid4(),
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in codes])],
    )


def fake_task(company_id):
    now = datetime.now(timezone.utc)
    return TaskResponse(
        id=uuid4(),
        company_id=company_id,
        project_id=None,
        product_id=None,
        milestone_id=None,
        required_deliverable_id=None,
        title="Prepare client proposal",
        description=None,
        expected_output=None,
        status="ready",
        priority="high",
        owner_user_id=None,
        client_id=None,
        start_at=None,
        due_at=None,
        estimated_hours=None,
        completed_at=None,
        founder_notes=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )


def test_ai_assistant_read_routes_are_registered():
    paths = {(route.path, tuple(route.methods or ())) for route in ai_router.router.routes}
    assert ("/ai-assistant/tools", ("GET",)) in paths
    assert ("/ai-assistant/read", ("POST",)) in paths


def test_capability_list_is_filtered_by_authenticated_permissions():
    user = user_with_permissions("tasks.view")
    result = list_ai_read_tools(current_user=user)

    assert [tool["name"] for tool in result["tools"]] == ["get_tasks"]
    assert result["provider_connected"] is False


def test_task_read_executes_through_orchestrator_and_records_ai_audit(monkeypatch):
    user = user_with_permissions("tasks.view")
    db = FakeDB()
    task = fake_task(user.company_id)
    monkeypatch.setattr(ai_router, "list_tasks", lambda **kwargs: [task])
    monkeypatch.setattr(ai_router.AIAuditRecorder, "record", lambda self, session, event: "audit-task-read")

    result = execute_ai_read(
        AIReadInvocation(message="Show my tasks", tool_name="get_tasks", input={}),
        current_user=user,
        db=db,
    )

    assert result.response_type is AIResponseType.ANSWER
    assert result.intent == "get_tasks"
    assert result.data["items"][0]["title"] == "Prepare client proposal"
    assert result.audit_reference == "audit-task-read"
    assert db.commits == 1


def test_global_search_read_uses_existing_company_scoped_search_surface(monkeypatch):
    user = user_with_permissions("global_search.view")
    db = FakeDB()
    record_id = uuid4()
    captured = {}

    def search(**kwargs):
        captured.update(kwargs)
        return {
            "query": kwargs["q"],
            "count": 1,
            "results": [{
                "type": "project",
                "id": str(record_id),
                "title": "Saru POS",
                "subtitle": "Delivery",
                "status": "active",
            }],
        }

    monkeypatch.setattr(ai_router, "global_search", search)
    monkeypatch.setattr(ai_router.AIAuditRecorder, "record", lambda self, session, event: "audit-search")

    result = execute_ai_read(
        AIReadInvocation(
            message="Find Saru POS",
            tool_name="global_search",
            input={"query": "Saru POS", "entity_types": ["project"]},
        ),
        current_user=user,
        db=db,
    )

    assert captured["current_user"] is user
    assert captured["db"] is db
    assert captured["entity_type"] == "project"
    assert result.records[0].entity_id == record_id
    assert result.audit_reference == "audit-search"


def test_read_permission_denial_returns_safe_blocked_response():
    user = user_with_permissions()
    result = execute_ai_read(
        AIReadInvocation(message="Show all tasks", tool_name="get_tasks", input={}),
        current_user=user,
        db=FakeDB(),
    )

    assert result.response_type is AIResponseType.BLOCKED
    assert result.error_code == "permission_denied"
    assert "tasks.view" not in result.summary


def test_read_input_rejects_unknown_fields_before_tool_execution(monkeypatch):
    user = user_with_permissions("global_search.view")
    with pytest.raises(HTTPException) as exc:
        execute_ai_read(
            AIReadInvocation(
                message="Find project",
                tool_name="global_search",
                input={"query": "Saru POS", "entity_type": "project"},
            ),
            current_user=user,
            db=FakeDB(),
        )

    assert exc.value.status_code == 422


def test_tool_list_uses_exact_domain_api_permission_not_generic_registry_permission():
    generic_only = user_with_permissions("crm.view")
    exact_domain = user_with_permissions("crm.followups.view")

    generic_tools = list_ai_read_tools(current_user=generic_only)["tools"]
    domain_tools = list_ai_read_tools(current_user=exact_domain)["tools"]

    assert "get_followups" not in {tool["name"] for tool in generic_tools}
    assert "get_followups" in {tool["name"] for tool in domain_tools}


def test_task_filter_rejects_non_text_status():
    user = user_with_permissions("tasks.view")

    with pytest.raises(HTTPException) as exc:
        execute_ai_read(
            AIReadInvocation(
                message="Show tasks",
                tool_name="get_tasks",
                input={"status": 123},
            ),
            current_user=user,
            db=FakeDB(),
        )

    assert exc.value.status_code == 422


def test_provider_unavailable_is_reported_without_claiming_ai_inference():
    user = user_with_permissions("tasks.view", "global_search.view")
    result = list_ai_read_tools(current_user=user)

    assert result["provider_connected"] is False
    assert {tool["name"] for tool in result["tools"]} == {"get_tasks", "global_search"}


def test_write_preview_requires_permission_and_returns_confirmation_preview():
    user = user_with_permissions("tasks.create")
    result = preview_ai_write(
        AIWriteInvocation(
            message="Create a task to prepare the client proposal",
            tool_name="create_task",
            input={"title": "Prepare client proposal", "priority": "high"},
        ),
        current_user=user,
    )

    assert result.response_type is AIResponseType.ACTION_PREVIEW
    assert result.confirmation_required is True
    assert result.data["action"] == "Create task"
    assert result.data["task"]["title"] == "Prepare client proposal"
    assert result.data["preview_id"]


def test_write_preview_rejects_unknown_task_fields():
    user = user_with_permissions("tasks.create")

    with pytest.raises(HTTPException) as exc:
        preview_ai_write(
            AIWriteInvocation(
                message="Create task",
                tool_name="create_task",
                input={"title": "Prepare proposal", "is_admin": True},
            ),
            current_user=user,
        )

    assert exc.value.status_code == 422


def test_confirmed_task_write_uses_business_rules_and_audited_executor(monkeypatch):
    user = user_with_permissions("tasks.create", "rules_engine.evaluate")
    user.roles[0].name = "Founder"
    db = FakeDB()
    task = fake_task(user.company_id)
    task = task.model_copy(update={"title": "Prepare client proposal"})
    captured = {}

    class FakeExecutor:
        def __init__(self, session, *, failure_audit_session_factory):
            self.last_audit_reference = "audit-task-create"

        def execute(self, event, handler, **kwargs):
            captured["event"] = event
            result = handler(**kwargs)
            captured["result"] = result
            return result

    monkeypatch.setattr(ai_router, "evaluate_rules", lambda *args, **kwargs: SimpleNamespace(allowed=True, evaluations=[]))
    monkeypatch.setattr(ai_router, "AIAuditedActionExecutor", FakeExecutor)
    monkeypatch.setattr(ai_router, "create_task_record", lambda *args, **kwargs: task)

    invocation = AIWriteInvocation(
        message="Create a task to prepare the client proposal",
        tool_name="create_task",
        input={"title": "Prepare client proposal", "priority": "high"},
    )
    preview = preview_ai_write(invocation, current_user=user)
    result = confirm_ai_write(
        AIWriteConfirmation(
            message=invocation.message,
            tool_name=invocation.tool_name,
            input=invocation.input,
            preview_id=preview.data["preview_id"],
        ),
        current_user=user,
        db=db,
    )

    assert result.response_type is AIResponseType.ACTION_RESULT
    assert result.data["task"]["title"] == "Prepare client proposal"
    assert result.records[0].entity_type == "task"
    assert result.audit_reference == "audit-task-create"
    assert captured["event"].confirmation_state == "confirmation_validated"
    assert captured["event"].business_rule_decision == "allowed"
    assert db.commits == 1


def test_confirmed_task_write_rejects_payload_tampering():
    user = user_with_permissions("tasks.create")
    invocation = AIWriteInvocation(
        message="Create a task",
        tool_name="create_task",
        input={"title": "Prepare proposal"},
    )
    preview = preview_ai_write(invocation, current_user=user)

    with pytest.raises(HTTPException) as exc:
        confirm_ai_write(
            AIWriteConfirmation(
                message=invocation.message,
                tool_name=invocation.tool_name,
                input={"title": "Delete all records"},
                preview_id=preview.data["preview_id"],
            ),
            current_user=user,
            db=FakeDB(),
        )

    assert exc.value.status_code == 409


def test_write_preview_cannot_be_confirmed_by_another_user():
    creator = user_with_permissions("tasks.create")
    other_user = user_with_permissions("tasks.create")
    invocation = AIWriteInvocation(
        message="Create a task",
        tool_name="create_task",
        input={"title": "Prepare proposal"},
    )
    preview = preview_ai_write(invocation, current_user=creator)

    with pytest.raises(HTTPException) as exc:
        confirm_ai_write(
            AIWriteConfirmation(
                message=invocation.message,
                tool_name=invocation.tool_name,
                input=invocation.input,
                preview_id=preview.data["preview_id"],
            ),
            current_user=other_user,
            db=FakeDB(),
        )

    assert exc.value.status_code == 403
