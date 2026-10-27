"""Provider-neutral AI orchestration boundary."""

from typing import Callable

from .contracts import AIRequest, AIResponse, AIResponseType
from .registry import AIToolDefinition, AIToolRegistry


class AIOrchestrator:
    """Coordinates intent selection and approved tool execution.

    The orchestrator never receives a database session and never writes to the
    database directly. Domain APIs, RBAC, business rules and audit remain
    authoritative execution boundaries.
    """

    def __init__(self, registry: AIToolRegistry) -> None:
        self.registry = registry

    def validate_tool_selection(self, tool_name: str) -> AIToolDefinition:
        return self.registry.require(tool_name)

    def preview_write(self, request: AIRequest, tool_name: str) -> AIResponse:
        tool = self.validate_tool_selection(tool_name)
        if tool.action_kind.value != "write":
            return AIResponse(
                request_id=request.request_id,
                intent=tool_name,
                response_type=AIResponseType.ERROR,
                summary="The selected capability is not a write action.",
                error_code="AI_TOOL_ACTION_MISMATCH",
            )

        return AIResponse(
            request_id=request.request_id,
            intent=tool_name,
            response_type=AIResponseType.ACTION_PREVIEW,
            summary=f"Ready to preview the {tool.name} action.",
            confirmation_required=tool.requires_confirmation,
            actions_available=[tool.name],
            warnings=["Execution is not performed by the architecture foundation."],
        )

    def execute_read(self, request: AIRequest, tool_name: str, handler: Callable[..., object] | None = None) -> object:
        tool = self.validate_tool_selection(tool_name)
        if tool.action_kind.value != "read":
            raise ValueError("Only registered read tools may use execute_read")
        selected_handler = handler or tool.handler
        if selected_handler is None:
            raise RuntimeError(f"AI read tool has no execution handler: {tool.name}")
        return selected_handler(request=request, context=request.context)
