"""Explicit allow-list of capabilities available to the AI orchestrator."""

from dataclasses import dataclass
from typing import Any, Callable

from .contracts import AIActionKind


@dataclass(frozen=True, slots=True)
class AIToolDefinition:
    name: str
    purpose: str
    action_kind: AIActionKind
    required_permission: str | None
    allowed_entities: tuple[str, ...]
    requires_confirmation: bool
    handler: Callable[..., Any] | None = None


class AIToolRegistry:
    """In-memory registry; domain tools are registered explicitly by code.

    The registry is intentionally independent from database access and model/provider
    SDKs. A tool must be registered before an orchestrator can select it.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AIToolDefinition] = {}

    def register(self, tool: AIToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"AI tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AIToolDefinition | None:
        return self._tools.get(name)

    def require(self, name: str) -> AIToolDefinition:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"AI tool is not registered: {name}")
        return tool

    def list(self, action_kind: AIActionKind | None = None) -> tuple[AIToolDefinition, ...]:
        tools = tuple(self._tools.values())
        if action_kind is None:
            return tools
        return tuple(tool for tool in tools if tool.action_kind == action_kind)

    def names(self, action_kind: AIActionKind | None = None) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.list(action_kind))
