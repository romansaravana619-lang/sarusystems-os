import pytest
from fastapi import HTTPException

from app.projects.router import (
    DELIVERABLE_TRANSITIONS,
    MILESTONE_TRANSITIONS,
    PROJECT_TRANSITIONS,
    _requirements_complete,
    _validate_deliverable_transition,
    _validate_milestone_transition,
    _validate_transition,
)
from app.projects.schemas import ProjectCreate
from app.tasks.router import _validate_project_context


def test_project_creation_requires_name():
    with pytest.raises(ValueError):
        ProjectCreate(opportunity_id="00000000-0000-0000-0000-000000000001", name="")


def test_project_lifecycle_has_delivery_gates():
    assert "development" in PROJECT_TRANSITIONS["ready"]
    assert "completed" in PROJECT_TRANSITIONS["delivery"]
    assert PROJECT_TRANSITIONS["completed"] == set()


def test_requirements_gate_rejects_without_scope_or_requirements():
    class DB:
        def scalar(self, statement):
            return 0

    assert _requirements_complete(DB(), None) is False


def test_invalid_project_transition_is_409():
    class Project:
        id = None
        status = "requirements_pending"

    with pytest.raises(HTTPException) as exc:
        _validate_transition(None, Project(), "development")
    assert exc.value.status_code == 409


def test_project_status_catalog_is_explicit():
    assert {"requirements_pending", "ready", "development", "testing", "review", "delivery", "completed"} <= set(PROJECT_TRANSITIONS)


def test_project_task_handoff_rejects_cross_company_project():
    class DB:
        def get(self, model, project_id):
            return None

    with pytest.raises(HTTPException) as exc:
        _validate_project_context(DB(), "company", "project", None, None, None)
    assert exc.value.status_code == 400


def test_project_task_handoff_rejects_completed_project():
    class Project:
        company_id = "company"
        client_id = "client"
        status = "completed"

    class DB:
        def get(self, model, project_id):
            return Project()

    with pytest.raises(HTTPException) as exc:
        _validate_project_context(DB(), "company", "project", None, None, "client")
    assert exc.value.status_code == 409


def test_project_task_handoff_requires_matching_client():
    class Project:
        company_id = "company"
        client_id = "client-a"
        status = "development"

    class DB:
        def get(self, model, project_id):
            return Project()

    with pytest.raises(HTTPException) as exc:
        _validate_project_context(DB(), "company", "project", None, None, "client-b")
    assert exc.value.status_code == 409


def test_milestone_lifecycle_is_explicit():
    assert "review" in MILESTONE_TRANSITIONS["in_progress"]
    assert "completed" in MILESTONE_TRANSITIONS["review"]
    assert MILESTONE_TRANSITIONS["completed"] == set()


def test_milestone_cannot_skip_lifecycle():
    class Milestone:
        status = "pending"

    with pytest.raises(HTTPException) as exc:
        _validate_milestone_transition(Milestone(), "completed")
    assert exc.value.status_code == 409


def test_deliverable_lifecycle_is_explicit():
    assert "in_review" in DELIVERABLE_TRANSITIONS["submitted"]
    assert "revision_required" in DELIVERABLE_TRANSITIONS["in_review"]
    assert "approved" in DELIVERABLE_TRANSITIONS["in_review"]
    assert DELIVERABLE_TRANSITIONS["approved"] == set()


def test_deliverable_approval_requires_final_approval():
    class Deliverable:
        status = "in_review"
        final_approval = False

    with pytest.raises(HTTPException) as exc:
        _validate_deliverable_transition(Deliverable(), "approved")
    assert exc.value.status_code == 409
