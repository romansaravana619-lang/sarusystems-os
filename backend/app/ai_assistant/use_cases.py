"""Approved 4.23.2 AI Company Assistant use-case catalogue.

This layer defines the implementation-facing intent catalogue only. It does not
execute tools, access the database, or make authorization decisions.
"""

from dataclasses import dataclass
from enum import StrEnum

from .contracts import AIActionKind


class AIUseCaseCategory(StrEnum):
    ATTENTION = "attention"
    SALES = "sales"
    PROJECTS = "projects"
    FINANCE = "finance"
    OPERATIONS = "operations"
    SEARCH = "search"
    SUMMARIZATION = "summarization"
    ACTIONS = "actions"
    INTELLIGENCE = "intelligence"


@dataclass(frozen=True, slots=True)
class AIUseCaseDefinition:
    key: str
    category: AIUseCaseCategory
    action_kind: AIActionKind
    purpose: str
    confirmation_required: bool
    advisory_only: bool = False


READ = AIActionKind.READ
WRITE = AIActionKind.WRITE


APPROVED_AI_USE_CASES: tuple[AIUseCaseDefinition, ...] = (
    AIUseCaseDefinition("today_attention", AIUseCaseCategory.ATTENTION, READ, "What needs my attention today?", False),
    AIUseCaseDefinition("today_priorities", AIUseCaseCategory.ATTENTION, READ, "Show today's priorities.", False),
    AIUseCaseDefinition("overdue_tasks", AIUseCaseCategory.ATTENTION, READ, "Show overdue tasks.", False),
    AIUseCaseDefinition("due_followups", AIUseCaseCategory.ATTENTION, READ, "Show follow-ups that are due.", False),
    AIUseCaseDefinition("prospect_followups", AIUseCaseCategory.SALES, READ, "Show prospects needing follow-up.", False),
    AIUseCaseDefinition("important_opportunities", AIUseCaseCategory.SALES, READ, "Show important sales opportunities.", False),
    AIUseCaseDefinition("sales_pipeline", AIUseCaseCategory.SALES, READ, "Show the current sales pipeline.", False),
    AIUseCaseDefinition("expected_pipeline_value", AIUseCaseCategory.SALES, READ, "Show expected pipeline value.", False),
    AIUseCaseDefinition("pending_proposals", AIUseCaseCategory.SALES, READ, "Show proposals awaiting response.", False),
    AIUseCaseDefinition("project_risks", AIUseCaseCategory.PROJECTS, READ, "Show projects at risk or delayed.", False),
    AIUseCaseDefinition("upcoming_milestones", AIUseCaseCategory.PROJECTS, READ, "Show upcoming project milestones.", False),
    AIUseCaseDefinition("blocking_tasks", AIUseCaseCategory.PROJECTS, READ, "Show blocking project tasks.", False),
    AIUseCaseDefinition("unpaid_client_payments", AIUseCaseCategory.FINANCE, READ, "Show unpaid or overdue client payments.", False),
    AIUseCaseDefinition("revenue_expenses", AIUseCaseCategory.FINANCE, READ, "Show revenue and expenses.", False),
    AIUseCaseDefinition("project_profitability_risk", AIUseCaseCategory.FINANCE, READ, "Show project profitability or financial risk.", False),
    AIUseCaseDefinition("freelancer_workload", AIUseCaseCategory.OPERATIONS, READ, "Show freelancer workload.", False),
    AIUseCaseDefinition("upcoming_calendar", AIUseCaseCategory.OPERATIONS, READ, "Show upcoming meetings and deadlines.", False),
    AIUseCaseDefinition("important_communications", AIUseCaseCategory.OPERATIONS, READ, "Show recent important communications.", False),
    AIUseCaseDefinition("notifications_attention", AIUseCaseCategory.OPERATIONS, READ, "Show notifications needing attention.", False),
    AIUseCaseDefinition("global_search", AIUseCaseCategory.SEARCH, READ, "Search company records across the OS.", False),
    AIUseCaseDefinition("client_summary", AIUseCaseCategory.SUMMARIZATION, READ, "Summarize a client.", False),
    AIUseCaseDefinition("project_summary", AIUseCaseCategory.SUMMARIZATION, READ, "Summarize a project.", False),
    AIUseCaseDefinition("opportunity_summary", AIUseCaseCategory.SUMMARIZATION, READ, "Summarize an opportunity.", False),
    AIUseCaseDefinition("business_area_summary", AIUseCaseCategory.SUMMARIZATION, READ, "Summarize a business area.", False),
    AIUseCaseDefinition("project_risk_explanation", AIUseCaseCategory.SUMMARIZATION, READ, "Explain why a project or opportunity is at risk.", False),
    AIUseCaseDefinition("create_followup_task", AIUseCaseCategory.ACTIONS, WRITE, "Create a follow-up task.", True),
    AIUseCaseDefinition("create_linked_task", AIUseCaseCategory.ACTIONS, WRITE, "Create a task linked to a client, prospect, or project.", True),
    AIUseCaseDefinition("schedule_followup", AIUseCaseCategory.ACTIONS, WRITE, "Schedule a follow-up.", True),
    AIUseCaseDefinition("create_founder_reminder", AIUseCaseCategory.ACTIONS, WRITE, "Create a Founder reminder.", True),
    AIUseCaseDefinition("record_activity", AIUseCaseCategory.ACTIONS, WRITE, "Record a communication or activity.", True),
    AIUseCaseDefinition("create_notification", AIUseCaseCategory.ACTIONS, WRITE, "Create an approved notification.", True),
    AIUseCaseDefinition("update_allowed_task_field", AIUseCaseCategory.ACTIONS, WRITE, "Update an allowed task field.", True),
    AIUseCaseDefinition("archive_allowed_record", AIUseCaseCategory.ACTIONS, WRITE, "Archive an allowed record action where supported by the underlying API.", True),
    AIUseCaseDefinition("complete_allowed_record_action", AIUseCaseCategory.ACTIONS, WRITE, "Complete an allowed record action where supported by the underlying API.", True),
    AIUseCaseDefinition("recommend_next_best_action", AIUseCaseCategory.INTELLIGENCE, READ, "Recommend a next best action.", False, True),
    AIUseCaseDefinition("identify_operational_anomalies", AIUseCaseCategory.INTELLIGENCE, READ, "Identify unusual operational conditions.", False, True),
    AIUseCaseDefinition("recommend_followup_priorities", AIUseCaseCategory.INTELLIGENCE, READ, "Recommend follow-up priorities.", False, True),
    AIUseCaseDefinition("detect_delivery_risk", AIUseCaseCategory.INTELLIGENCE, READ, "Detect project delivery risk.", False, True),
    AIUseCaseDefinition("detect_payment_risk", AIUseCaseCategory.INTELLIGENCE, READ, "Detect payment risk.", False, True),
    AIUseCaseDefinition("weekly_performance_summary", AIUseCaseCategory.INTELLIGENCE, READ, "Summarize weekly performance.", False, True),
    AIUseCaseDefinition("founder_daily_briefing", AIUseCaseCategory.INTELLIGENCE, READ, "Generate a Founder daily briefing.", False, True),
)

_USE_CASES_BY_KEY = {item.key: item for item in APPROVED_AI_USE_CASES}


def get_use_case(key: str) -> AIUseCaseDefinition | None:
    """Return one approved use case without executing it."""
    return _USE_CASES_BY_KEY.get(key)


def list_use_cases(action_kind: AIActionKind | None = None) -> tuple[AIUseCaseDefinition, ...]:
    """List approved use cases, optionally restricted to read or write."""
    if action_kind is None:
        return APPROVED_AI_USE_CASES
    return tuple(item for item in APPROVED_AI_USE_CASES if item.action_kind == action_kind)
