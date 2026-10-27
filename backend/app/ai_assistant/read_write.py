"""Explicit read/write execution boundaries for the AI Company Assistant."""

from dataclasses import dataclass
from typing import Any

from .contracts import AIActionKind
from .registry import AIToolDefinition, AIToolRegistry


@dataclass(frozen=True, slots=True)
class AIActionDecision:
    """Decision produced before any AI tool execution."""

    tool_name: str
    action_kind: AIActionKind
    allowed: bool
    confirmation_required: bool
    reason: str


class AIReadWritePolicy:
    """Enforces the finalized 4.23.4 read-vs-write boundary."""

    def __init__(self, registry: AIToolRegistry) -> None:
        self.registry = registry

    def classify(self, tool_name: str) -> AIActionKind:
        return self.registry.require(tool_name).action_kind

    def decide(self, tool_name: str, *, confirmation_granted: bool = False) -> AIActionDecision:
        tool = self.registry.require(tool_name)
        if tool.action_kind == AIActionKind.READ:
            return AIActionDecision(tool_name, tool.action_kind, True, False, "read_action_allowed")
        if not confirmation_granted:
            return AIActionDecision(tool_name, tool.action_kind, False, True, "write_confirmation_required")
        return AIActionDecision(tool_name, tool.action_kind, True, True, "write_confirmation_granted")

    def validate_request(self, tool: AIToolDefinition, payload: dict[str, Any]) -> None:
        schema = tool.input_schema
        required = schema.get("required", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(f"Missing required tool fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        unknown = set(payload) - set(properties)
        if schema.get("additionalProperties") is False and unknown:
            raise ValueError(f"Unknown tool fields: {', '.join(sorted(unknown))}")


def ensure_read_action(policy: AIReadWritePolicy, tool_name: str, payload: dict[str, Any]) -> AIActionDecision:
    tool = policy.registry.require(tool_name)
    if tool.action_kind != AIActionKind.READ:
        raise PermissionError("Only read tools may pass the read-only execution boundary")
    policy.validate_request(tool, payload)
    return policy.decide(tool_name)


def ensure_write_action(
    policy: AIReadWritePolicy,
    tool_name: str,
    payload: dict[str, Any],
    *,
    confirmation_granted: bool,
) -> AIActionDecision:
    tool = policy.registry.require(tool_name)
    if tool.action_kind != AIActionKind.WRITE:
        raise PermissionError("Only write tools may pass the write execution boundary")
    policy.validate_request(tool, payload)
    decision = policy.decide(tool_name, confirmation_granted=confirmation_granted)
    if not decision.allowed:
        return decision
    return decision
