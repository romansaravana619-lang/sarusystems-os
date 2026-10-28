"""Explicit allow-list and contracts for AI-callable SaruSystems OS tools."""

from dataclasses import dataclass, field
from typing import Any, Callable

from .contracts import AIActionKind

@dataclass(frozen=True, slots=True)
class AIToolDefinition:
    """Complete implementation contract for one AI-callable capability."""
    name: str
    purpose: str
    action_kind: AIActionKind
    required_permission: str | None
    allowed_entities: tuple[str, ...]
    requires_confirmation: bool
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object", "additionalProperties": False})
    output_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    validation_rules: tuple[str, ...] = ()
    business_rule_requirements: tuple[str, ...] = ()
    audit_event: str = "ai.tool.unclassified"
    failure_behavior: tuple[str, ...] = ()
    use_case_key: str = ""
    handler: Callable[..., Any] | None = None

class AIToolRegistry:
    """Explicit in-memory allow-list; no database or provider access."""
    def __init__(self, tools: tuple[AIToolDefinition, ...] = ()) -> None:
        self._tools: dict[str, AIToolDefinition] = {}
        for tool in tools:
            self.register(tool)
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
    def __len__(self) -> int:
        return len(self._tools)

def _tool(name: str, purpose: str, action_kind: AIActionKind, input_schema: dict[str, Any], output_schema: dict[str, Any], permission: str | None, entities: tuple[str, ...], validation: tuple[str, ...], rules: tuple[str, ...], confirmation: bool, audit_event: str, failures: tuple[str, ...], use_case: str) -> AIToolDefinition:
    return AIToolDefinition(name=name, purpose=purpose, action_kind=action_kind, input_schema=input_schema, output_schema=output_schema, required_permission=permission, allowed_entities=entities, validation_rules=validation, business_rule_requirements=rules, requires_confirmation=confirmation, audit_event=audit_event, failure_behavior=failures, use_case_key=use_case)

READ = AIActionKind.READ
WRITE = AIActionKind.WRITE
_QUERY_IN = {"type": "object", "additionalProperties": False}
_QUERY_OUT = {"type": "object", "properties": {"items": {"type": "array"}}, "required": ["items"]}

def _read(name: str, purpose: str, permission: str, entities: tuple[str, ...], use_case: str, *, fields: dict[str, Any] | None = None, rules: tuple[str, ...] = ("company_scope", "domain_api_authorization")) -> AIToolDefinition:
    schema = dict(_QUERY_IN)
    if fields:
        schema["properties"] = fields
    return _tool(name, purpose, READ, schema, _QUERY_OUT, permission, entities, ("validate_input_schema", "resolve_entity_scope", "reject_unknown_fields"), rules, False, f"ai.tool.read.{name}", ("missing_data_return_unavailable", "permission_denied_without_leakage", "api_failure_no_success_claim"), use_case)

AI_READ_TOOLS: tuple[AIToolDefinition, ...] = (
    _read("get_today_attention", "Return Founder attention items for today.", "command_center.view", ("task", "followup", "approval", "alert"), "today_attention"),
    _read("get_tasks", "Retrieve tasks in the user's permitted scope.", "tasks.view", ("task",), "overdue_tasks", fields={"status": {"type": "string"}, "due_before": {"type": "string"}}),
    _read("get_followups", "Retrieve due or upcoming follow-ups.", "crm.view", ("prospect", "client", "opportunity", "followup"), "due_followups"),
    _read("get_sales_pipeline", "Return the current sales pipeline.", "sales.pipeline.view", ("opportunity", "proposal"), "sales_pipeline"),
    _read("get_prospect_followups", "Return prospects requiring follow-up.", "crm.view", ("prospect", "contact", "followup"), "prospect_followups"),
    _read("get_opportunities", "Retrieve permitted sales opportunities.", "sales.pipeline.view", ("opportunity",), "important_opportunities"),
    _read("get_proposals", "Retrieve proposals and response status.", "sales.pipeline.view", ("proposal", "opportunity"), "pending_proposals"),
    _read("get_projects", "Retrieve permitted projects.", "projects.view", ("project", "milestone", "task"), "project_summary"),
    _read("get_project_risks", "Return projects with delivery or financial risk.", "projects.view", ("project", "risk", "task"), "project_risks"),
    _read("get_project_milestones", "Return upcoming project milestones.", "projects.view", ("project", "milestone"), "upcoming_milestones"),
    _read("get_unpaid_payments", "Return unpaid or overdue client payments.", "finance.dashboard.view", ("client_payment", "project", "client"), "unpaid_client_payments", rules=("company_scope", "finance_access", "domain_api_authorization")),
    _read("get_financial_summary", "Return permitted revenue and expense summary.", "finance.dashboard.view", ("payment", "expense", "project"), "revenue_expenses", rules=("company_scope", "finance_access", "domain_api_authorization")),
    _read("get_freelancer_workload", "Return freelancer workload and assignments.", "freelancers.view", ("freelancer", "assignment", "task"), "freelancer_workload"),
    _read("get_calendar_events", "Return upcoming permitted calendar events.", "calendar.view", ("calendar_event", "meeting", "deadline"), "upcoming_calendar"),
    _read("get_notifications", "Return notifications requiring attention.", "notifications.view", ("notification",), "notifications_attention"),
    _read("get_communication_history", "Return permitted communication and activity history.", "communication.view", ("communication", "activity", "client", "prospect"), "important_communications"),
    _read("get_client_summary", "Return a structured summary for one client.", "clients.view", ("client", "contact", "project", "payment", "communication"), "client_summary", fields={"client_id": {"type": "string", "format": "uuid"}}),
    _read("get_project_summary", "Return a structured summary for one project.", "projects.view", ("project", "milestone", "task", "payment", "risk"), "project_summary", fields={"project_id": {"type": "string", "format": "uuid"}}),
    _read("get_opportunity_summary", "Return a structured summary for one opportunity.", "sales.pipeline.view", ("opportunity", "prospect", "proposal"), "opportunity_summary", fields={"opportunity_id": {"type": "string", "format": "uuid"}}),
    _read("global_search", "Search company records through the 4.22 Global Search surface.", "global_search.view", ("prospect", "client", "project", "opportunity", "proposal", "task", "payment", "document", "communication", "contact"), "global_search", fields={"query": {"type": "string", "minLength": 1}, "entity_types": {"type": "array"}}),
    _read("get_analytics_summary", "Return permitted business analytics summary.", "analytics.dashboard.view", ("analytics", "sales", "project", "finance", "marketing", "content"), "business_area_summary", rules=("company_scope", "analytics_access", "domain_api_authorization")),
)

_WRITE_COMMON_VALIDATION = ("validate_input_schema", "resolve_entity_scope", "validate_target_exists", "reject_unknown_fields")
_WRITE_COMMON_RULES = ("company_scope", "permission_check", "business_rules_engine", "domain_api_authorization")
_WRITE_FAILURES = ("validation_failure_no_write", "permission_denied_no_mutation", "business_rule_blocked_no_mutation", "api_failure_no_success_claim", "partial_failure_report_explicitly")

AI_WRITE_TOOLS: tuple[AIToolDefinition, ...] = (
    _tool("create_task", "Create a task through the Task API after confirmation.", WRITE, {"type": "object", "required": ["title"], "properties": {"title": {"type": "string", "minLength": 1}, "due_date": {"type": "string"}, "priority": {"type": "string"}, "assignee_id": {"type": "string", "format": "uuid"}}}, {"type": "object", "required": ["record_id"], "properties": {"record_id": {"type": "string", "format": "uuid"}}}, "task.create", ("task",), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES, True, "ai.tool.write.create_task", _WRITE_FAILURES, "create_linked_task"),
    _tool("create_followup", "Create a follow-up through the CRM/domain API after confirmation.", WRITE, {"type": "object", "required": ["target_id", "due_at"], "properties": {"target_id": {"type": "string", "format": "uuid"}, "due_at": {"type": "string"}, "notes": {"type": "string"}}}, {"type": "object", "required": ["record_id"]}, "crm.followup.create", ("prospect", "client", "opportunity", "followup"), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES, True, "ai.tool.write.create_followup", _WRITE_FAILURES, "create_followup_task"),
    _tool("schedule_followup", "Schedule a follow-up or reminder through Calendar after confirmation.", WRITE, {"type": "object", "required": ["target_id", "scheduled_at"], "properties": {"target_id": {"type": "string", "format": "uuid"}, "scheduled_at": {"type": "string"}, "title": {"type": "string"}}}, {"type": "object", "required": ["record_id"]}, "calendar.event.create", ("calendar_event", "followup", "prospect", "client"), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES, True, "ai.tool.write.schedule_followup", _WRITE_FAILURES, "schedule_followup"),
    _tool("create_founder_reminder", "Create a Founder reminder through Calendar after confirmation.", WRITE, {"type": "object", "required": ["title", "remind_at"], "properties": {"title": {"type": "string", "minLength": 1}, "remind_at": {"type": "string"}}}, {"type": "object", "required": ["record_id"]}, "calendar.event.create", ("calendar_event", "founder_reminder"), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES, True, "ai.tool.write.create_founder_reminder", _WRITE_FAILURES, "create_founder_reminder"),
    _tool("record_activity", "Record an allowed communication/activity through the Communication API after confirmation.", WRITE, {"type": "object", "required": ["activity_type", "summary"], "properties": {"activity_type": {"type": "string"}, "summary": {"type": "string", "minLength": 1}, "target_id": {"type": "string", "format": "uuid"}}}, {"type": "object", "required": ["record_id"]}, "communication.create", ("communication", "activity", "client", "prospect", "project"), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES + ("external_communication_never_auto_sent",), True, "ai.tool.write.record_activity", _WRITE_FAILURES, "record_activity"),
    _tool("create_notification", "Create an approved notification through Notification API after confirmation.", WRITE, {"type": "object", "required": ["title", "recipient_id"], "properties": {"title": {"type": "string"}, "recipient_id": {"type": "string", "format": "uuid"}, "body": {"type": "string"}, "priority": {"type": "string"}}}, {"type": "object", "required": ["record_id"]}, "notification.create", ("notification", "user"), _WRITE_COMMON_VALIDATION, _WRITE_COMMON_RULES + ("recipient_scope_validation",), True, "ai.tool.write.create_notification", _WRITE_FAILURES, "create_notification"),
    _tool("update_task", "Update an allowed task field through the Task API after confirmation.", WRITE, {"type": "object", "required": ["task_id", "field", "value"], "properties": {"task_id": {"type": "string", "format": "uuid"}, "field": {"type": "string"}, "value": {}}}, {"type": "object", "required": ["record_id", "updated_field"]}, "task.update", ("task",), _WRITE_COMMON_VALIDATION + ("field_allow_list",), _WRITE_COMMON_RULES, True, "ai.tool.write.update_task", _WRITE_FAILURES, "update_allowed_task_field"),
    _tool("update_allowed_record", "Update a record only where the underlying domain API explicitly permits the field/action.", WRITE, {"type": "object", "required": ["entity_type", "record_id", "field", "value"], "properties": {"entity_type": {"type": "string"}, "record_id": {"type": "string", "format": "uuid"}, "field": {"type": "string"}, "value": {}}, {"type": "object", "required": ["record_id", "entity_type", "updated_field"]}, "domain.update", ("task", "prospect", "client", "project", "opportunity"), _WRITE_COMMON_VALIDATION + ("entity_field_allow_list",), _WRITE_COMMON_RULES, True, "ai.tool.write.update_allowed_record", _WRITE_FAILURES, "update_allowed_record"),
)

APPROVED_AI_TOOLS: tuple[AIToolDefinition, ...] = AI_READ_TOOLS + AI_WRITE_TOOLS
DEFAULT_AI_TOOL_REGISTRY = AIToolRegistry(APPROVED_AI_TOOLS)

def get_default_ai_tool_registry() -> AIToolRegistry:
    """Return a fresh registry containing only approved 4.23.3 tools."""
    return AIToolRegistry(APPROVED_AI_TOOLS)
