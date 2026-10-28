"""AI Safety / Confirmation policy boundary."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

READ_ACTIONS = frozenset({
    "get_today_attention", "get_tasks", "get_followups", "get_sales_pipeline",
    "get_prospect_followups", "get_opportunities", "get_proposals", "get_projects",
    "get_project_risks", "get_project_milestones", "get_unpaid_payments",
    "get_financial_summary", "get_freelancer_workload", "get_calendar_events",
    "get_notifications", "get_communication_history", "get_client_summary",
    "get_project_summary", "get_opportunity_summary", "global_search", "get_analytics_summary",
})
CONFIRMATION_REQUIRED_ACTIONS = frozenset({
    "create_task", "create_followup", "schedule_followup", "create_founder_reminder",
    "record_activity", "create_notification", "update_task", "update_allowed_record",
})
ALWAYS_BLOCKED_ACTIONS = frozenset({
    "change_permissions", "change_roles", "delete_critical_record", "execute_payment",
    "send_external_communication", "bypass_business_rules", "change_security_configuration",
})

@dataclass(frozen=True, slots=True)
class AISafetyDecision:
    action: str
    classification: str
    confirmation_required: bool
    blocked: bool
    reason_code: str

@dataclass(frozen=True, slots=True)
class AIConfirmationPreview:
    confirmation_id: UUID
    request_id: UUID
    action: str
    target_entity_type: str | None
    target_entity_id: UUID | None
    important_fields: dict[str, Any] = field(default_factory=dict)
    expected_impact: str = ""

@dataclass(frozen=True, slots=True)
class AIConfirmation:
    confirmation_id: UUID
    request_id: UUID
    action: str

class AISafetyPolicy:
    """Classify AI actions and enforce explicit confirmation boundaries."""

    def classify(self, action: str) -> AISafetyDecision:
        if action in ALWAYS_BLOCKED_ACTIONS:
            return AISafetyDecision(action, "always_blocked", False, True, "action_not_permitted_by_ai_safety_policy")
        if action in CONFIRMATION_REQUIRED_ACTIONS:
            return AISafetyDecision(action, "confirmation_required", True, False, "explicit_confirmation_required")
        if action in READ_ACTIONS:
            return AISafetyDecision(action, "safe_read", False, False, "safe_read_action")
        return AISafetyDecision(action, "unknown", False, True, "unregistered_ai_action")

    def preview(self, *, request_id: UUID, action: str, target_entity_type: str | None = None,
                target_entity_id: UUID | None = None, important_fields: dict[str, Any] | None = None,
                expected_impact: str = "") -> AIConfirmationPreview:
        decision = self.classify(action)
        if decision.blocked:
            raise PermissionError(decision.reason_code)
        if not decision.confirmation_required:
            raise ValueError("Confirmation preview is only valid for confirmation-required actions")
        return AIConfirmationPreview(
            confirmation_id=uuid4(), request_id=request_id, action=action,
            target_entity_type=target_entity_type, target_entity_id=target_entity_id,
            important_fields=dict(important_fields or {}), expected_impact=expected_impact,
        )

    def ensure_executable(self, *, request_id: UUID, action: str,
                          confirmation: AIConfirmation | None = None,
                          preview: AIConfirmationPreview | None = None) -> None:
        decision = self.classify(action)
        if decision.blocked:
            raise PermissionError(decision.reason_code)
        if not decision.confirmation_required:
            return
        if preview is None or confirmation is None:
            raise PermissionError("explicit_confirmation_required")
        if confirmation.confirmation_id != preview.confirmation_id:
            raise PermissionError("confirmation_mismatch")
        if confirmation.request_id != request_id or preview.request_id != request_id:
            raise PermissionError("confirmation_request_mismatch")
        if confirmation.action != action or preview.action != action:
            raise PermissionError("confirmation_action_mismatch")

def classify_ai_action(action: str) -> AISafetyDecision:
    return AISafetyPolicy().classify(action)
