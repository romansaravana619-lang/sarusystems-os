"""Safety and explicit-confirmation boundary for AI write actions.

A write is previewed, explicitly confirmed against its exact request/tool/payload,
and executed only with a valid single-use confirmation ticket.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
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
    preview_id: UUID = field(default_factory=uuid4)


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
    """Hash strict canonical JSON; reject non-JSON values and non-finite numbers."""
    if not isinstance(payload, dict):
        raise TypeError("AI write payload must be a JSON object")
    _validate_json_value(payload, "payload")
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite JSON numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} object keys must be strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} contains a value that is not JSON serializable")


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Confirmation timestamps must be timezone-aware")
    return value


class AISafetyPolicy:
    """Enforce explicit, exact-payload, time-limited, single-use confirmation."""

    DEFAULT_TTL = timedelta(minutes=10)

    def __init__(self, registry: AIToolRegistry, *, ttl: timedelta | None = None) -> None:
        self.registry = registry
        self.ttl = ttl if ttl is not None else self.DEFAULT_TTL
        if self.ttl <= timedelta(0):
            raise ValueError("Confirmation ticket TTL must be greater than zero")
        self._previews: dict[UUID, AIWritePreview] = {}
        self._tickets: dict[UUID, AIConfirmationTicket] = {}

    def preview_write(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
    ) -> AIWritePreview:
        tool = self.registry.require(tool_name)
        self._validate_write_tool(tool)
        self._validate_payload(tool, payload)
        preview = AIWritePreview(
            request_id=request.request_id,
            tool_name=tool.name,
            payload_hash=canonical_payload_hash(payload),
            summary=self._summary(tool, payload),
            confirmation_required=True,
            warnings=self._warnings(tool),
        )
        self._previews[preview.preview_id] = preview
        return preview

    def issue_confirmation(
        self,
        preview: AIWritePreview,
        *,
        now: datetime | None = None,
    ) -> AIConfirmationTicket:
        stored_preview = self._previews.get(preview.preview_id)
        if stored_preview is None or stored_preview != preview:
            raise PermissionError("A confirmation can only be issued for a preview created by this policy")
        if not preview.confirmation_required:
            raise ValueError("A write preview must require confirmation")

        issued_at = _require_aware_datetime(now or datetime.now(timezone.utc))
        self._previews.pop(preview.preview_id, None)
        self._tickets = {
            ticket_id: ticket
            for ticket_id, ticket in self._tickets.items()
            if ticket.expires_at > issued_at and not ticket.consumed
        }
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

        current_time = _require_aware_datetime(now or datetime.now(timezone.utc))
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
        return AISafetyDecision(
            True,
            True,
            "confirmation_validated",
            ticket=consumed_ticket,
        )

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
            return AISafetyDecision(
                False,
                True,
                "explicit_confirmation_required",
                preview=preview,
            )
        return self.confirm_write(request, tool_name, payload, confirmation_id, now=now)

    @staticmethod
    def _validate_write_tool(tool: AIToolDefinition) -> None:
        if tool.action_kind != AIActionKind.WRITE:
            raise PermissionError("Only registered write tools may pass the AI safety boundary")
        if not tool.requires_confirmation:
            raise PermissionError("AI write tools must require explicit confirmation")

    @classmethod
    def _validate_payload(cls, tool: AIToolDefinition, payload: dict[str, Any]) -> None:
        canonical_payload_hash(payload)
        cls._validate_schema_value(tool.input_schema, payload, "payload")

    @classmethod
    def _validate_schema_value(cls, schema: dict[str, Any], value: Any, path: str) -> None:
        expected_type = schema.get("type")
        type_checks = {
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "boolean": lambda item: isinstance(item, bool),
            "null": lambda item: item is None,
        }
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if expected_type is not None and not any(
            type_checks.get(type_name, lambda _: False)(value) for type_name in allowed_types
        ):
            raise ValueError(f"{path} must match schema type {expected_type}")

        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path} must be one of the allowed values")

        if isinstance(value, dict):
            properties = schema.get("properties", {})
            missing = [key for key in schema.get("required", []) if key not in value]
            if missing:
                raise ValueError(f"{path} is missing required fields: {', '.join(missing)}")
            unknown = set(value) - set(properties)
            additional = schema.get("additionalProperties", True)
            if additional is False and unknown:
                raise ValueError(f"{path} contains unknown fields: {', '.join(sorted(unknown))}")
            for key, item in value.items():
                if key in properties:
                    cls._validate_schema_value(properties[key], item, f"{path}.{key}")
                elif isinstance(additional, dict):
                    cls._validate_schema_value(additional, item, f"{path}.{key}")

        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                raise ValueError(f"{path} is shorter than the allowed minimum")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                raise ValueError(f"{path} exceeds the allowed maximum length")
            if schema.get("format") == "uuid":
                try:
                    parsed_uuid = UUID(value)
                except ValueError as exc:
                    raise ValueError(f"{path} must be a valid UUID") from exc
                if str(parsed_uuid) != value.lower():
                    raise ValueError(f"{path} must use the canonical UUID format")

        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                raise ValueError(f"{path} contains fewer than the allowed items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                raise ValueError(f"{path} contains more than the allowed items")
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    cls._validate_schema_value(item_schema, item, f"{path}[{index}]")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise ValueError(f"{path} is below the allowed minimum")
            if "maximum" in schema and value > schema["maximum"]:
                raise ValueError(f"{path} exceeds the allowed maximum")

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
