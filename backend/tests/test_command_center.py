from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.dependencies import require_permission
from app.command_center.action_schemas import FounderActionCreate, FounderActionUpdate


def _user_with_roles(*permission_groups: list[str]):
    roles = [
        SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in permissions])
        for permissions in permission_groups
    ]
    return SimpleNamespace(roles=roles)


def test_founder_action_requires_operational_fields() -> None:
    owner_id = uuid4()
    action = FounderActionCreate(
        category="project",
        source_module="projects",
        priority="high",
        description="Client approval is pending",
        required_action="Follow up with the client and record the decision",
        owner_user_id=owner_id,
        due_date=date(2026, 10, 30),
    )
    assert action.owner_user_id == owner_id
    assert action.priority == "high"


def test_founder_action_rejects_empty_description() -> None:
    with pytest.raises(ValidationError):
        FounderActionCreate(
            category="project",
            source_module="projects",
            description="",
            required_action="Follow up",
            owner_user_id=uuid4(),
        )


def test_founder_action_update_supports_closure() -> None:
    update = FounderActionUpdate(status="done", founder_notes="Decision completed")
    assert update.status == "done"
    assert update.founder_notes == "Decision completed"


def test_command_center_action_permissions_are_separate() -> None:
    user = _user_with_roles(["command_center.view"])
    with pytest.raises(HTTPException) as exc_info:
        require_permission("command_center.actions.create")(user)
    assert exc_info.value.status_code == 403


def test_command_center_action_permission_allows_authorized_founder() -> None:
    user = _user_with_roles(["command_center.actions.create", "command_center.actions.edit"])
    assert require_permission("command_center.actions.create")(user) is user
    assert require_permission("command_center.actions.edit")(user) is user
