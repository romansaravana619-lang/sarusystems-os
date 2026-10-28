"""RBAC boundary for AI-callable SaruSystems OS tools.

The AI layer never gains privileges of its own.  A request is authorized using
only the authenticated user's permissions and company scope; domain APIs remain
the final enforcement point.
"""

from dataclasses import dataclass
from uuid import UUID

from .registry import AIToolDefinition


@dataclass(frozen=True, slots=True)
class AIAuthorizationContext:
    """Security principal supplied by the authenticated OS request context."""

    user_id: UUID
    company_id: UUID
    permission_codes: frozenset[str]


@dataclass(frozen=True, slots=True)
class AIAuthorizationDecision:
    """Non-sensitive authorization result safe for the AI orchestration layer."""

    allowed: bool
    reason_code: str
    tool_name: str
    required_permission: str | None
    user_id: UUID
    company_id: UUID


class AIToolRBACPolicy:
    """Authorize AI tools without creating an AI-specific privilege elevation path."""

    def authorize(
        self,
        tool: AIToolDefinition,
        context: AIAuthorizationContext,
        *,
        target_company_id: UUID | None = None,
    ) -> AIAuthorizationDecision:
        if target_company_id is not None and target_company_id != context.company_id:
            return AIAuthorizationDecision(
                allowed=False,
                reason_code="company_scope_denied",
                tool_name=tool.name,
                required_permission=tool.required_permission,
                user_id=context.user_id,
                company_id=context.company_id,
            )

        permission = tool.required_permission
        if permission is not None and permission not in context.permission_codes:
            return AIAuthorizationDecision(
                allowed=False,
                reason_code="permission_denied",
                tool_name=tool.name,
                required_permission=permission,
                user_id=context.user_id,
                company_id=context.company_id,
            )

        return AIAuthorizationDecision(
            allowed=True,
            reason_code="allowed",
            tool_name=tool.name,
            required_permission=permission,
            user_id=context.user_id,
            company_id=context.company_id,
        )

    @staticmethod
    def permission_codes_from_user(current_user: object) -> frozenset[str]:
        """Extract permissions from the authenticated OS User/Role graph.

        The helper intentionally accepts the ORM object structurally so the AI
        policy does not import or depend on a specific database model.
        """
        roles = getattr(current_user, "roles", ())
        return frozenset(
            permission.code
            for role in roles
            for permission in getattr(role, "permissions", ())
            if getattr(permission, "code", None)
        )

    def authorize_user(
        self,
        tool: AIToolDefinition,
        current_user: object,
        *,
        target_company_id: UUID | None = None,
    ) -> AIAuthorizationDecision:
        """Build the security context from the authenticated OS user."""
        user_id = getattr(current_user, "id", None)
        company_id = getattr(current_user, "company_id", None)
        if not isinstance(user_id, UUID) or not isinstance(company_id, UUID):
            raise ValueError("Authenticated user must provide UUID id and company_id")
        context = AIAuthorizationContext(
            user_id=user_id,
            company_id=company_id,
            permission_codes=self.permission_codes_from_user(current_user),
        )
        return self.authorize(tool, context, target_company_id=target_company_id)


def authorize_ai_tool(
    tool: AIToolDefinition,
    current_user: object,
    *,
    target_company_id: UUID | None = None,
) -> AIAuthorizationDecision:
    """Convenience boundary for orchestrators and future API adapters."""
    return AIToolRBACPolicy().authorize_user(
        tool,
        current_user,
        target_company_id=target_company_id,
    )
