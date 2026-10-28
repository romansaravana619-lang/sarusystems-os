"""Audit boundary for AI Company Assistant actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class AIAuditContext:
    user_id: UUID
    company_id: UUID
    request_id: UUID
    user_request: str
    normalized_intent: str
    tool_name: str
    target_entity_type: str | None = None
    target_entity_id: UUID | None = None
    input_metadata: dict[str, Any] = field(default_factory=dict)
    permission_decision: str = "not_evaluated"
    business_rule_decision: str = "not_evaluated"
    confirmation_state: str = "not_required"
    execution_result: str = "not_executed"
    resulting_record_ids: tuple[UUID, ...] = ()
    error_code: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AIAuditRecord:
    audit_reference: str
    context: AIAuditContext


class AIAuditSink(Protocol):
    def record(self, context: AIAuditContext) -> AIAuditRecord:
        """Persist through the authoritative OS audit boundary."""


class AIAuditPolicy:
    """Validate and forward AI audit context without provider-specific data."""

    def __init__(self, sink: AIAuditSink) -> None:
        self._sink = sink

    def record(self, context: AIAuditContext) -> AIAuditRecord:
        if not context.user_request.strip():
            raise ValueError("user_request must not be empty")
        if not context.normalized_intent.strip():
            raise ValueError("normalized_intent must not be empty")
        if not context.tool_name.strip():
            raise ValueError("tool_name must not be empty")
        if context.target_entity_id is not None and not context.target_entity_type:
            raise ValueError("target_entity_type is required when target_entity_id is set")
        return self._sink.record(context)


def record_ai_audit(
    sink: AIAuditSink,
    *,
    user_id: UUID,
    company_id: UUID,
    request_id: UUID,
    user_request: str,
    normalized_intent: str,
    tool_name: str,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    input_metadata: dict[str, Any] | None = None,
    permission_decision: str = "not_evaluated",
    business_rule_decision: str = "not_evaluated",
    confirmation_state: str = "not_required",
    execution_result: str = "not_executed",
    resulting_record_ids: tuple[UUID, ...] = (),
    error_code: str | None = None,
) -> AIAuditRecord:
    """Record a minimal, provider-neutral AI audit event."""
    context = AIAuditContext(
        user_id=user_id,
        company_id=company_id,
        request_id=request_id,
        user_request=user_request,
        normalized_intent=normalized_intent,
        tool_name=tool_name,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        input_metadata=dict(input_metadata or {}),
        permission_decision=permission_decision,
        business_rule_decision=business_rule_decision,
        confirmation_state=confirmation_state,
        execution_result=execution_result,
        resulting_record_ids=resulting_record_ids,
        error_code=error_code,
    )
    return AIAuditPolicy(sink).record(context)
