from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.tasks.router import TASK_STATUS_TRANSITIONS, _validate_status
from app.tasks.schemas import ChecklistCreate, TaskCreate, TaskUpdate


def test_task_create_defaults_to_backlog_and_medium() -> None:
    payload = TaskCreate(title="Prepare proposal")
    assert payload.status == "backlog"
    assert payload.priority == "medium"


def test_task_status_workflow_matches_approved_lifecycle() -> None:
    assert TASK_STATUS_TRANSITIONS["backlog"] == {"ready", "cancelled"}
    assert "in_progress" in TASK_STATUS_TRANSITIONS["ready"]
    assert "review" in TASK_STATUS_TRANSITIONS["in_progress"]
    assert "revision" in TASK_STATUS_TRANSITIONS["review"]
    assert "completed" in TASK_STATUS_TRANSITIONS["review"]


def test_task_status_transition_rejects_skipping_lifecycle() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_status("backlog", "review")
    assert exc_info.value.status_code == 409


def test_task_terminal_states_cannot_reopen() -> None:
    for status in ("completed", "cancelled", "done"):
        with pytest.raises(HTTPException) as exc_info:
            _validate_status(status, "in_progress")
        assert exc_info.value.status_code == 409


def test_task_payload_accepts_project_execution_fields() -> None:
    payload = TaskCreate(
        title="Build landing page",
        project_id=uuid4(),
        milestone_id=uuid4(),
        required_deliverable_id=uuid4(),
        expected_output="Responsive production page",
        start_at=None,
        estimated_hours=8,
        founder_notes="Founder review required before submission",
    )
    assert payload.estimated_hours == 8
    assert payload.expected_output
    assert payload.founder_notes


def test_task_payload_accepts_client_and_owner_scope() -> None:
    payload = TaskUpdate(owner_user_id=uuid4(), client_id=uuid4(), due_at=None)
    assert payload.owner_user_id is not None
    assert payload.client_id is not None


def test_checklist_requires_title() -> None:
    payload = ChecklistCreate(title="Verify deliverable")
    assert payload.title == "Verify deliverable"
