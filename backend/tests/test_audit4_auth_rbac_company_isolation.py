from types import SimpleNamespace
from uuid import uuid4

from fastapi.security import HTTPAuthorizationCredentials

import app.auth.dependencies as auth_dependencies
import app.auth.router as auth_router


class _FakeDB:
    def __init__(self, result):
        self.result = result
        self.statements = []
        self.added = []
        self.committed = False

    def scalar(self, statement):
        self.statements.append(statement)
        return self.result

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True


def _active_user():
    return SimpleNamespace(id=uuid4(), company_id=uuid4(), is_active=True, roles=[])


def test_current_user_lookup_requires_active_company(monkeypatch):
    user = _active_user()
    db = _FakeDB(user)
    monkeypatch.setattr(auth_dependencies, "decode_access_token", lambda _: user.id)

    result = auth_dependencies.get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        db,
    )

    assert result is user
    sql = str(db.statements[0])
    assert "companies.is_active" in sql
    assert "users.is_active" in sql


def test_login_lookup_requires_active_company(monkeypatch):
    user = _active_user()
    db = _FakeDB(user)
    monkeypatch.setattr(auth_router, "verify_password", lambda password, password_hash: True)
    monkeypatch.setattr(auth_router, "create_access_token", lambda user_id: "token")

    response = auth_router.login(SimpleNamespace(email="user@example.com", password="secret"), db)

    assert response.access_token == "token"
    sql = str(db.statements[0])
    assert "companies.is_active" in sql
    assert "users.is_active" in sql
    assert db.committed is True
