from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.tasks.router import _validate_status
from app.tasks.schemas import ChecklistCreate, TaskCreate, TaskUpdate


def test_task_create_defaults_to_backlog_and_medium() -> None:
    payload = TaskCreate(title="Prepare proposal")
    assert payload.status == "backlog"
    assert payload.priority == "medium"


def test_task_status_transition_rejects_skipping_lifecycle() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_status("backlog", "review")
    assert exc_info.value.status_code == 409


def test_task_terminal_states_cannot_reopen() -> None:
    for status in ("done", "cancelled"):
        with pytest.raises(HTTPException) as exc_info:
            _validate_status(status, "in_progress")
        assert exc_info.value.status_code == 409


def test_task_payload_accepts_client_and_owner_scope() -> None:
    payload = TaskUpdate(owner_user_id=uuid4(), client_id=uuid4(), due_at=None)
    assert payload.owner_user_id is not None
    assert payload.client_id is not None


def test_checklist_requires_title() -> None:
    payload = ChecklistCreate(title="Verify deliverable")
    assert payload.title == "Verify deliverable"
