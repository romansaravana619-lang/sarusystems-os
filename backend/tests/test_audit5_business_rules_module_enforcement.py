from types import SimpleNamespace
from uuid import uuid4

import app.rules.router as rules_router


class _FakeDB:
    def __init__(self, rules):
        self.rules = rules
        self.added = []
        self.committed = False

    def scalars(self, statement):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return self.rules

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True


def _user():
    return SimpleNamespace(id=uuid4(), company_id=uuid4())


def _payload():
    return SimpleNamespace(
        trigger_event="project.status_change",
        applies_to="project",
        action="complete_project",
        context={"approved_scope": True},
        user_id=None,
        role_names=(),
    )


def _rule(*, blocked=False):
    return SimpleNamespace(
        id=uuid4(),
        rule_key="project.completion",
        name="Project completion rule",
        required_conditions={},
        prohibited_conditions={},
        required_actions=[],
        prohibited_actions=[],
        allowed_roles=[],
        allowed_user_ids=[],
        enforcement_mode="block" if blocked else "warn",
    )


def test_rule_evaluation_records_an_audit_decision(monkeypatch):
    user = _user()
    db = _FakeDB([_rule(blocked=False)])
    monkeypatch.setattr(rules_router, "_matches", lambda context, expected: True)

    response = rules_router.evaluate_rules(_payload(), user, db)

    assert response.allowed is True
    assert db.committed is True
    assert len(db.added) == 1
    audit = db.added[0]
    assert audit.action == "business_rule.evaluate"
    assert audit.entity_type == "BusinessRuleEvaluation"
    assert audit.actor_user_id == user.id
    assert '"allowed": true' in audit.details


def test_blocked_rule_decision_is_audited_and_denied(monkeypatch):
    user = _user()
    db = _FakeDB([_rule(blocked=True)])
    monkeypatch.setattr(rules_router, "_matches", lambda context, expected: False)

    response = rules_router.evaluate_rules(_payload(), user, db)

    assert response.allowed is False
    assert response.evaluations[0].blocked is True
    assert db.committed is True
    assert len(db.added) == 1
    audit = db.added[0]
    assert audit.action == "business_rule.evaluate"
    assert '"allowed": false' in audit.details
    assert str(response.evaluations[0].rule_id) in audit.details
