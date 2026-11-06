"""Provider-neutral AI orchestration boundary."""

from typing import Any, Callable, Protocol
from uuid import UUID

from .audit import AIAuditEvent
from .business_rules import AIBusinessRuleDecision
from .contracts import AIActionKind, AIRequest, AIResponse, AIResponseType
from .rbac import AIAuthorizationDecision
from .read_write import AIReadWritePolicy
from .registry import AIToolDefinition, AIToolRegistry
from .safety import AIConfirmationTicket, AISafetyPolicy, AIWritePreview


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
    Meaningful writes must pass its own confirmation policy, permission and
    business-rule checks, then execute through the audited execution boundary.
    """

    def __init__(
        self,
        registry: AIToolRegistry,
        *,
        action_executor: AuditedActionExecutor | None = None,
        safety_policy: AISafetyPolicy | None = None,
    ) -> None:
        self.registry = registry
        self.action_executor = action_executor
        self.safety_policy = safety_policy or AISafetyPolicy(registry)
        if self.safety_policy.registry is not registry:
            raise ValueError("The AI safety policy must use the orchestrator's tool registry")

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

    def preview_write_action(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
    ) -> AIWritePreview:
        """Create an exact-payload preview owned by this orchestrator's safety policy."""
        return self.safety_policy.preview_write(request, tool_name, payload)

    def issue_write_confirmation(
        self,
        preview: AIWritePreview,
    ) -> AIConfirmationTicket:
        """Issue a single-use ticket only for a preview created by this policy."""
        return self.safety_policy.issue_confirmation(preview)

    def execute_write(
        self,
        request: AIRequest,
        tool_name: str,
        payload: dict[str, Any],
        *,
        confirmation_id: UUID | None,
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

        if self.action_executor is None:
            raise RuntimeError("An audited action executor is required for AI write execution")

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
            or audit_event.action_payload_hash != self.safety_policy_hash(payload)
        ):
            raise PermissionError("The audit context does not match the approved action decisions")

        safety_decision = self.safety_policy.authorize_write_execution(
            request,
            tool_name,
            payload,
            confirmation_id,
        )
        if not safety_decision.allowed or safety_decision.ticket is None:
            raise PermissionError(f"AI write confirmation rejected: {safety_decision.reason}")

        return self.action_executor.execute(
            audit_event,
            handler,
            request=request,
            context=request.context,
            payload=payload,
        )

    @staticmethod
    def safety_policy_hash(payload: dict[str, Any]) -> str:
        from .safety import canonical_payload_hash

        return canonical_payload_hash(payload)

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
