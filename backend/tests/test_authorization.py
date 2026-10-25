from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_permission


def _user_with_roles(*permission_groups: list[str]):
    roles = [
        SimpleNamespace(
            permissions=[SimpleNamespace(code=code) for code in permissions]
        )
        for permissions in permission_groups
    ]
    return SimpleNamespace(roles=roles)


def test_required_permission_allows_access() -> None:
    user = _user_with_roles(["users.view"])

    assert require_permission("users.view")(user) is user


def test_command_center_requires_explicit_permission() -> None:
    user = _user_with_roles(["users.view"])

    with pytest.raises(HTTPException) as exc_info:
        require_permission("command_center.view")(user)

    assert exc_info.value.status_code == 403


def test_command_center_permission_allows_founder_access() -> None:
    user = _user_with_roles(["command_center.view"])

    assert require_permission("command_center.view")(user) is user


def test_missing_permission_returns_forbidden() -> None:
    user = _user_with_roles(["users.create"])

    with pytest.raises(HTTPException) as exc_info:
        require_permission("users.view")(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have permission to perform this action."


def test_permission_is_exact_match() -> None:
    user = _user_with_roles(["users.view.all"])

    with pytest.raises(HTTPException) as exc_info:
        require_permission("users.view")(user)

    assert exc_info.value.status_code == 403


def test_permission_can_be_granted_by_any_assigned_role() -> None:
    user = _user_with_roles(["users.view"], ["roles.view"])

    assert require_permission("roles.view")(user) is user
