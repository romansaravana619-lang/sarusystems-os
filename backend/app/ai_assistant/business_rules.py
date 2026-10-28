"""Business-rule boundary for AI actions.

The AI layer delegates policy evaluation to the existing SaruSystems OS
business-rules engine. It never evaluates or bypasses persisted rules itself.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AIBusinessRuleRequest:
    """Normalized rule-evaluation context for an AI action."""

    trigger_event: str
    applies_to: str
    action: str | None
    context: dict[str, object]
    user_id: UUID | None
    role_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AIBusinessRuleDecision:
    """Safe decision returned to the AI orchestration layer."""

    allowed: bool
    reason_code: str
    blocked: bool
    trigger_event: str
    applies_to: str
    action: str | None
    evaluation_count: int
    warnings: tuple[str, ...] = ()


class BusinessRuleEvaluator(Protocol):
    """Adapter boundary for the authoritative 4.16 rules-engine API/service."""

    def evaluate(self, request: AIBusinessRuleRequest) -> object: ...


class AIBusinessRulesPolicy:
    """Enforce 4.16 business rules before an AI write may execute."""

    @staticmethod
    def _decision_from_result(
        request: AIBusinessRuleRequest,
        result: object,
    ) -> AIBusinessRuleDecision:
        allowed = bool(getattr(result, "allowed", False))
        evaluations = tuple(getattr(result, "evaluations", ()) or ())
        warnings = tuple(
            reason
            for evaluation in evaluations
            if not bool(getattr(evaluation, "blocked", False))
            for reason in (getattr(evaluation, "reasons", ()) or ())
        )
        return AIBusinessRuleDecision(
            allowed=allowed,
            reason_code="allowed" if allowed else "business_rule_blocked",
            blocked=not allowed,
            trigger_event=request.trigger_event,
            applies_to=request.applies_to,
            action=request.action,
            evaluation_count=len(evaluations),
            warnings=warnings,
        )

    def evaluate(
        self,
        request: AIBusinessRuleRequest,
        evaluator: BusinessRuleEvaluator,
    ) -> AIBusinessRuleDecision:
        if not request.trigger_event.strip():
            raise ValueError("Business-rule trigger_event is required")
        if not request.applies_to.strip():
            raise ValueError("Business-rule applies_to is required")
        result = evaluator.evaluate(request)
        return self._decision_from_result(request, result)

    def ensure_allowed(
        self,
        request: AIBusinessRuleRequest,
        evaluator: BusinessRuleEvaluator,
    ) -> AIBusinessRuleDecision:
        decision = self.evaluate(request, evaluator)
        if decision.blocked:
            raise PermissionError("AI action blocked by business rules")
        return decision


def evaluate_ai_business_rules(
    request: AIBusinessRuleRequest,
    evaluator: BusinessRuleEvaluator,
) -> AIBusinessRuleDecision:
    """Convenience boundary for the AI orchestrator/API adapter."""
    return AIBusinessRulesPolicy().evaluate(request, evaluator)
