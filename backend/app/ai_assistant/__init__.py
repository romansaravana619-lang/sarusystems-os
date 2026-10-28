"""SaruSystems OS AI Company Assistant domain foundation."""

from .audit import AIAuditEvent, AIAuditRecorder, record_ai_audit
from .business_rules import (
    AIBusinessRuleDecision,
    AIBusinessRuleRequest,
    AIBusinessRulesPolicy,
    BusinessRuleEvaluator,
    evaluate_ai_business_rules,
)
from .contracts import AIActionKind, AIRequest, AIResponse, AIResponseType
from .failure import AIFailureHandler, AIFailureKind
from .global_search import (
    AIGlobalSearchResolver,
    AIEntityResolution,
    AISearchContext,
    AISearchResult,
    resolve_ai_entity,
)
from .orchestrator import AIOrchestrator
from .rbac import (
    AIAuthorizationContext,
    AIAuthorizationDecision,
    AIToolRBACPolicy,
    authorize_ai_tool,
)
from .registry import (
    AI_READ_TOOLS,
    AI_WRITE_TOOLS,
    APPROVED_AI_TOOLS,
    AIToolDefinition,
    AIToolRegistry,
    get_default_ai_tool_registry,
)
from .response import AIResponseContract, validate_response
from .safety import (
    AIConfirmationTicket,
    AISafetyDecision,
    AISafetyPolicy,
    AIWritePreview,
    canonical_payload_hash,
)

__all__ = [
    "AIActionKind",
    "AIRequest",
    "AIResponse",
    "AIResponseType",
    "AIResponseContract",
    "validate_response",
    "AIFailureHandler",
    "AIFailureKind",
    "AIOrchestrator",
    "AIToolDefinition",
    "AIToolRegistry",
    "AI_READ_TOOLS",
    "AI_WRITE_TOOLS",
    "APPROVED_AI_TOOLS",
    "get_default_ai_tool_registry",
    "AIAuthorizationContext",
    "AIAuthorizationDecision",
    "AIToolRBACPolicy",
    "authorize_ai_tool",
    "AIBusinessRuleDecision",
    "AIBusinessRuleRequest",
    "AIBusinessRulesPolicy",
    "BusinessRuleEvaluator",
    "evaluate_ai_business_rules",
    "AIGlobalSearchResolver",
    "AIEntityResolution",
    "AISearchContext",
    "AISearchResult",
    "resolve_ai_entity",
    "AIAuditEvent",
    "AIAuditRecorder",
    "record_ai_audit",
    "AIConfirmationTicket",
    "AISafetyDecision",
    "AISafetyPolicy",
    "AIWritePreview",
    "canonical_payload_hash",
]
