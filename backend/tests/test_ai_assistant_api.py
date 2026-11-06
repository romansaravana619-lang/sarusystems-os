from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.ai_assistant import router as ai_router
from app.ai_assistant.contracts import AIResponseType
from app.ai_assistant.router import AIReadInvocation, execute_ai_read, list_ai_read_tools
from app.tasks.schemas import TaskResponse


class FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


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
