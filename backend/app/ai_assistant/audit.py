"""Audit boundary for meaningful AI Company Assistant activity.

This module records structured AI audit context through the existing OS AuditLog
model. It deliberately contains no provider-specific logic and never stores
provider credentials or unnecessary secrets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.shared.models import AuditLog


class AuditSession(Protocol):
    def add(self, instance: AuditLog) -> None: ...

    def flush(self) -> None: ...


@dataclass(frozen=True, slots=True)
class AIAuditEvent:
    """Minimum traceable context required for a meaningful AI action."""

    user_id: UUID
    company_id: UUID
    request_id: UUID
    normalized_intent: str | None
    tool_name: str
    target_entity_type: str | None = None
    target_entity_id: UUID | None = None
    action_metadata: dict[str, Any] = field(default_factory=dict)
    permission_decision: str | None = None
    business_rule_decision: str | None = None
    confirmation_state: str | None = None
    execution_result: str | None = None
    resulting_record_ids: tuple[UUID, ...] = ()
    failure_error: str | None = None
    read_only: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_details(self) -> str:
        """Serialize safe audit metadata without secrets or provider credentials."""
        payload = {
            "audit_version": 1,
            "company_id": str(self.company_id),
            "request_id": str(self.request_id),
            "timestamp": self.timestamp.isoformat(),
            "normalized_intent": self.normalized_intent,
            "tool_name": self.tool_name,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": str(self.target_entity_id) if self.target_entity_id else None,
            "action_metadata": self.action_metadata,
            "permission_decision": self.permission_decision,
            "business_rule_decision": self.business_rule_decision,
            "confirmation_state": self.confirmation_state,
            "execution_result": self.execution_result,
            "resulting_record_ids": [str(value) for value in self.resulting_record_ids],
            "failure_error": self.failure_error,
            "read_only": self.read_only,
        }
        return json.dumps(payload, separators=(",", ":"), default=str)


class AIAuditRecorder:
    """Persist AI audit events through the existing AuditLog boundary."""

    ACTION = "ai_assistant"
    ENTITY_TYPE = "ai_request"

    def record(self, db: AuditSession, event: AIAuditEvent) -> str:
        audit_reference = str(uuid4())
        audit_log = AuditLog(
            actor_user_id=event.user_id,
            action=self.ACTION,
            entity_type=self.ENTITY_TYPE,
            entity_id=str(event.request_id),
            details=self._bounded_details(event, audit_reference),
        )
        db.add(audit_log)
        db.flush()
        return audit_reference

    @staticmethod
    def _bounded_details(event: AIAuditEvent, audit_reference: str) -> str:
        details = json.loads(event.to_details())
        details["audit_reference"] = audit_reference
        serialized = json.dumps(details, separators=(",", ":"), default=str)
        if len(serialized) > 4000:
            raise ValueError("AI audit metadata exceeds the AuditLog details limit")
        return serialized


def record_ai_audit(db: AuditSession, event: AIAuditEvent) -> str:
    """Convenience entry point for AI orchestration and tool execution layers."""
    return AIAuditRecorder().record(db, event)
