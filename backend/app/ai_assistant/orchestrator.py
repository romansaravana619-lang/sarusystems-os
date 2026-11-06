"""Provider-neutral AI orchestration boundary."""

from typing import Any, Callable, Protocol

from .audit import AIAuditEvent
from .contracts import AIActionKind, AIRequest, AIResponse, AIResponseType
from .business_rules import AIBusinessRuleDecision
from .rbac import AIAuthorizationDecision
from .read_write import AIReadWritePolicy
from .registry import AIToolDefinition, AIToolRegistry
from .safety import AISafetyDecision, canonical_payload_hash


class AuditedActionExecutor(Protocol):
    """Request-scoped execution adapter; database access stays outside the orchestrator."""

    def execute(
        self,
        event: AIAuditEvent,
        handler: Callable[..., Any],
        **handler_kwargs: Any,
    ) -> Any: ...


class AIOrchestrator:
    """Coordinate intent selection and delegate approved execution.

    The orchestrator never receives a database session or writes to the database.
    Meaningful write actions must pass safety, permission and business-rule checks,
    then execute through the injected audited execution boundary.
    """

    def __init__(
        self,
        registry: AIToolRegistry,
        *,
        action_executor: AuditedActionExecutor | None = None,
    ) -> None:
        self.registry = registry
        self.action_executor = action_executor

    def validate_tool_selection(self, tool_name: str) -> AIToolDefinition:
        return self.registry.require(tool_name)

    def preview_write(self, request: AIRequest, tool_name: str) -> AIResponse:
        tool = self.validate_tool_selection(tool_name)
        if tool.action_kind != AIActionKind.WRITE:
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
            warnings=["Execution requires explicit confirmation and an audited domain handler."],
        )

    def execute_write(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
        *,
        safety_decision: AISafetyDecision,
        authorization_decision: AIAuthorizationDecision,
        business_rule_decision: AIBusinessRuleDecision,
        audit_event: AIAuditEvent,
        handler: Callable[..., Any],
    ) -> Any:
        """Execute only a confirmed, authorized write through the audit boundary."""
        tool = self.validate_tool_selection(tool_name)
        if tool.action_kind != AIActionKind.WRITE or not tool.requires_confirmation:
            raise PermissionError("Only confirmation-protected write tools may be executed")

        AIReadWritePolicy(self.registry).validate_request(tool, payload)

        ticket = safety_decision.ticket
        if (
            not safety_decision.allowed
            or not safety_decision.confirmation_required
            or ticket is None
            or not ticket.consumed
            or ticket.request_id != request.request_id
            or ticket.tool_name != tool_name
            or ticket.payload_hash != canonical_payload_hash(payload)
        ):
            raise PermissionError("A valid, consumed confirmation for this exact action is required")

        if (
            not authorization_decision.allowed
            or authorization_decision.tool_name != tool_name
            or authorization_decision.required_permission != tool.required_permission
            or authorization_decision.user_id != audit_event.user_id
            or authorization_decision.company_id != audit_event.company_id
            or not business_rule_decision.allowed
            or business_rule_decision.blocked
            or audit_event.permission_decision != authorization_decision.reason_code
            or audit_event.business_rule_decision != business_rule_decision.reason_code
            or audit_event.read_only
            or audit_event.request_id != request.request_id
            or audit_event.user_request != request.message
            or audit_event.tool_name != tool_name
            or audit_event.permission_decision != "allowed"
            or audit_event.business_rule_decision != "allowed"
            or audit_event.confirmation_state not in {"confirmed", "confirmation_validated"}
            or audit_event.action_payload_hash != canonical_payload_hash(payload)
        ):
            raise PermissionError("The audit context does not match the approved action decisions")

        if self.action_executor is None:
            raise RuntimeError("An audited action executor is required for AI write execution")

        return self.action_executor.execute(
            audit_event,
            handler,
            request=request,
            context=request.context,
            payload=payload,
        )

    def execute_read(
        self,
        request: AIRequest,
        tool_name: str,
        handler: Callable[..., object] | None = None,
    ) -> object:
        tool = self.validate_tool_selection(tool_name)
        if tool.action_kind != AIActionKind.READ:
            raise ValueError("Only registered read tools may use execute_read")
        selected_handler = handler or tool.handler
        if selected_handler is None:
            raise RuntimeError(f"AI read tool has no execution handler: {tool.name}")
        return selected_handler(request=request, context=request.context)
