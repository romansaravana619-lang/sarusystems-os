"""Safety and explicit-confirmation boundary for AI write actions.

This module keeps confirmation deterministic and provider-neutral. A write action
must be previewed first, then explicitly confirmed against the exact request,
tool and payload that were previewed. Confirmation tickets are single-use and
expire after a short bounded lifetime.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from .contracts import AIActionKind, AIRequest
from .registry import AIToolDefinition, AIToolRegistry


@dataclass(frozen=True, slots=True)
class AIWritePreview:
    """Immutable preview that defines exactly what the Founder is confirming."""

    request_id: UUID
    tool_name: str
    payload_hash: str
    summary: str
    confirmation_required: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AIConfirmationTicket:
    """Single-use confirmation capability bound to one exact preview."""

    confirmation_id: UUID
    request_id: UUID
    tool_name: str
    payload_hash: str
    issued_at: datetime
    expires_at: datetime
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class AISafetyDecision:
    """Result of the safety boundary before a write may execute."""

    allowed: bool
    confirmation_required: bool
    reason: str
    preview: AIWritePreview | None = None
    ticket: AIConfirmationTicket | None = None


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    """Hash canonical JSON so confirmation cannot silently drift with payload order."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AISafetyPolicy:
    """Enforce the approved 4.23.9 safety/confirmation contract."""

    DEFAULT_TTL = timedelta(minutes=10)

    def __init__(self, registry: AIToolRegistry, *, ttl: timedelta | None = None) -> None:
        self.registry = registry
        self.ttl = ttl or self.DEFAULT_TTL
        self._tickets: dict[UUID, AIConfirmationTicket] = {}

    def preview_write(self, request: AIRequest, tool_name: str, payload: dict[str, Any]) -> AIWritePreview:
        tool = self.registry.require(tool_name)
        self._validate_write_tool(tool)
        self._validate_payload(tool, payload)
        payload_hash = canonical_payload_hash(payload)
        return AIWritePreview(
            request_id=request.request_id,
            tool_name=tool.name,
            payload_hash=payload_hash,
            summary=self._summary(tool, payload),
            confirmation_required=True,
            warnings=self._warnings(tool),
        )

    def issue_confirmation(self, preview: AIWritePreview, *, now: datetime | None = None) -> AIConfirmationTicket:
        if not preview.confirmation_required:
            raise ValueError("A write preview must require confirmation")
        issued_at = now or datetime.now(timezone.utc)
        ticket = AIConfirmationTicket(
            confirmation_id=uuid4(),
            request_id=preview.request_id,
            tool_name=preview.tool_name,
            payload_hash=preview.payload_hash,
            issued_at=issued_at,
            expires_at=issued_at + self.ttl,
        )
        self._tickets[ticket.confirmation_id] = ticket
        return ticket

    def confirm_write(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
        confirmation_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AISafetyDecision:
        tool = self.registry.require(tool_name)
        self._validate_write_tool(tool)
        self._validate_payload(tool, payload)

        ticket = self._tickets.get(confirmation_id)
        if ticket is None:
            return AISafetyDecision(False, True, "confirmation_not_found")

        current_time = now or datetime.now(timezone.utc)
        if current_time >= ticket.expires_at:
            return AISafetyDecision(False, True, "confirmation_expired")
        if ticket.consumed:
            return AISafetyDecision(False, True, "confirmation_already_used")
        if ticket.request_id != request.request_id or ticket.tool_name != tool_name:
            return AISafetyDecision(False, True, "confirmation_context_mismatch")
        if ticket.payload_hash != canonical_payload_hash(payload):
            return AISafetyDecision(False, True, "confirmation_payload_mismatch")

        consumed_ticket = AIConfirmationTicket(
            confirmation_id=ticket.confirmation_id,
            request_id=ticket.request_id,
            tool_name=ticket.tool_name,
            payload_hash=ticket.payload_hash,
            issued_at=ticket.issued_at,
            expires_at=ticket.expires_at,
            consumed=True,
        )
        self._tickets[confirmation_id] = consumed_ticket
        return AISafetyDecision(True, True, "confirmation_validated", ticket=consumed_ticket)

    def authorize_write_execution(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
        confirmation_id: UUID | None,
        *,
        now: datetime | None = None,
    ) -> AISafetyDecision:
        """Return a safe execution decision; never auto-authorize a write."""
        if confirmation_id is None:
            preview = self.preview_write(request, tool_name, payload)
            return AISafetyDecision(False, True, "explicit_confirmation_required", preview=preview)
        return self.confirm_write(request, tool_name, payload, confirmation_id, now=now)

    @staticmethod
    def _validate_write_tool(tool: AIToolDefinition) -> None:
        if tool.action_kind != AIActionKind.WRITE:
            raise PermissionError("Only registered write tools may pass the AI safety boundary")
        if not tool.requires_confirmation:
            raise PermissionError("AI write tools must require explicit confirmation")

    @staticmethod
    def _validate_payload(tool: AIToolDefinition, payload: dict[str, Any]) -> None:
        required = tool.input_schema.get("required", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(f"Missing required tool fields: {', '.join(missing)}")
        properties = tool.input_schema.get("properties", {})
        if tool.input_schema.get("additionalProperties") is False:
            unknown = set(payload) - set(properties)
            if unknown:
                raise ValueError(f"Unknown tool fields: {', '.join(sorted(unknown))}")

    @staticmethod
    def _summary(tool: AIToolDefinition, payload: dict[str, Any]) -> str:
        if tool.name == "create_task":
            return f"Create task: {payload.get('title')}"
        if tool.name == "create_followup":
            return f"Create CRM follow-up for target {payload.get('target_id')}"
        if tool.name == "schedule_followup":
            return f"Schedule follow-up for target {payload.get('target_id')}"
        if tool.name == "create_founder_reminder":
            return f"Create Founder reminder: {payload.get('title')}"
        if tool.name == "record_activity":
            return f"Record activity: {payload.get('summary')}"
        if tool.name == "create_notification":
            return f"Create notification: {payload.get('title')}"
        return f"Execute approved AI write action: {tool.name}"

    @staticmethod
    def _warnings(tool: AIToolDefinition) -> tuple[str, ...]:
        warnings = ["No write is executed until explicit confirmation is validated."]
        if "external_communication_never_auto_sent" in tool.business_rule_requirements:
            warnings.append("External communication is never sent automatically by the AI layer.")
        return tuple(warnings)
