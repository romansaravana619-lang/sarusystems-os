from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai_assistant.business_rules import (
    AIBusinessRuleRequest,
    AIBusinessRulesPolicy,
    evaluate_ai_business_rules,
)


class FakeEvaluator:
    def __init__(self, *, allowed: bool, blocked: bool, reasons: tuple[str, ...] = ()) -> None:
        self.result = SimpleNamespace(
            allowed=allowed,
            evaluations=[
                SimpleNamespace(
                    blocked=blocked,
                    reasons=reasons,
                )
            ]
        )
        self.requests = []

    def evaluate(self, request: AIBusinessRuleRequest) -> object:
        self.requests.append(request)
        return self.result


def request() -> AIBusinessRuleRequest:
    return AIBusinessRuleRequest(
        trigger_event="ai.task.create",
        applies_to="task",
        action="create_task",
        context={"priority": "high"},
        user_id=uuid4(),
        role_names=("Founder",),
    )


def test_business_rule_policy_delegates_to_authoritative_engine() -> None:
    evaluator = FakeEvaluator(allowed=True, blocked=False)

    decision = AIBusinessRulesPolicy().evaluate(request(), evaluator)

    assert decision.allowed is True
    assert decision.blocked is False
    assert decision.reason_code == "allowed"
    assert evaluator.requests == [request()]


def test_blocked_business_rule_cannot_be_bypassed() -> None:
    evaluator = FakeEvaluator(
        allowed=False,
        blocked=True,
        reasons=("Project requirements are not approved.",),
    )

    decision = AIBusinessRulesPolicy().evaluate(request(), evaluator)

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.reason_code == "business_rule_blocked"
    assert decision.evaluation_count == 1
    assert decision.warnings == ()

    with pytest.raises(PermissionError, match="blocked by business rules"):
        AIBusinessRulesPolicy().ensure_allowed(request(), evaluator)


def test_non_blocking_rule_reasons_are_returned_as_warnings() -> None:
    evaluator = FakeEvaluator(
        allowed=True,
        blocked=False,
        reasons=("Review recommended before execution.",),
    )

    decision = evaluate_ai_business_rules(request(), evaluator)

    assert decision.allowed is True
    assert decision.blocked is False
    assert decision.warnings == ("Review recommended before execution.",)


def test_invalid_business_rule_request_is_rejected_before_evaluation() -> None:
    evaluator = FakeEvaluator(allowed=True, blocked=False)
    invalid = AIBusinessRuleRequest(
        trigger_event=" ",
        applies_to="task",
        action="create_task",
        context={},
        user_id=None,
        role_names=(),
    )

    with pytest.raises(ValueError, match="trigger_event is required"):
        AIBusinessRulesPolicy().evaluate(invalid, evaluator)

    assert evaluator.requests == []


def test_empty_target_scope_is_rejected_before_evaluation() -> None:
    evaluator = FakeEvaluator(allowed=True, blocked=False)
    invalid = AIBusinessRuleRequest(
        trigger_event="ai.task.create",
        applies_to=" ",
        action="create_task",
        context={},
        user_id=None,
        role_names=(),
    )

    with pytest.raises(ValueError, match="applies_to is required"):
        AIBusinessRulesPolicy().evaluate(invalid, evaluator)

    assert evaluator.requests == []
