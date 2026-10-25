from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_permission


def _dependency_for(permissions: list[str]):
    user = SimpleNamespace(
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in permissions])]
    )
    return require_permission("users.view")(user)


def test_required_permission_allows_access() -> None:
    user = _dependency_for(["users.view"])
    assert user is not None


def test_missing_permission_returns_forbidden() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _dependency_for(["users.create"])

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have permission to perform this action."


def test_permission_is_exact_match() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _dependency_for(["users.view.all"])

    assert exc_info.value.status_code == 403
