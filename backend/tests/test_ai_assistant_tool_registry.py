import pytest

from app.ai_assistant.contracts import AIActionKind
from app.ai_assistant.registry import (
    AI_READ_TOOLS,
    AI_WRITE_TOOLS,
    APPROVED_AI_TOOLS,
    AIToolDefinition,
    AIToolRegistry,
    get_default_ai_tool_registry,
)


EXPECTED_READ_TOOLS = {
    "get_today_attention",
    "get_tasks",
    "get_followups",
    "get_sales_pipeline",
    "get_prospect_followups",
    "get_opportunities",
    "get_proposals",
    "get_projects",
    "get_project_risks",
    "get_project_milestones",
    "get_unpaid_payments",
    "get_financial_summary",
    "get_freelancer_workload",
    "get_calendar_events",
    "get_notifications",
    "get_communication_history",
    "get_client_summary",
    "get_project_summary",
    "get_opportunity_summary",
    "global_search",
    "get_analytics_summary",
}
EXPECTED_WRITE_TOOLS = {
    "create_task",
    "create_followup",
    "schedule_followup",
    "create_founder_reminder",
    "record_activity",
    "create_notification",
    "update_task",
    "update_allowed_record",
}


def test_approved_tool_catalog_matches_4_23_3_allow_list() -> None:
    assert {tool.name for tool in AI_READ_TOOLS} == EXPECTED_READ_TOOLS
    assert {tool.name for tool in AI_WRITE_TOOLS} == EXPECTED_WRITE_TOOLS
    assert len(APPROVED_AI_TOOLS) == 29
    assert len({tool.name for tool in APPROVED_AI_TOOLS}) == 29


def test_every_tool_has_complete_registry_contract() -> None:
    for tool in APPROVED_AI_TOOLS:
        assert tool.name
        assert tool.purpose
        assert tool.input_schema["type"] == "object"
        assert tool.output_schema["type"] == "object"
        assert tool.allowed_entities
        assert tool.validation_rules
        assert tool.business_rule_requirements
        assert tool.audit_event.startswith("ai.tool.")
        assert tool.failure_behavior
        assert tool.use_case_key
        assert tool.handler is None, "4.23.3 must not execute domain APIs yet"


def test_write_tools_are_confirmation_required_and_reads_are_not() -> None:
    assert all(tool.requires_confirmation for tool in AI_WRITE_TOOLS)
    assert all(not tool.requires_confirmation for tool in AI_READ_TOOLS)
    assert all(tool.action_kind is AIActionKind.WRITE for tool in AI_WRITE_TOOLS)
    assert all(tool.action_kind is AIActionKind.READ for tool in AI_READ_TOOLS)


def test_registry_enforces_explicit_allow_list_and_duplicate_rejection() -> None:
    registry = get_default_ai_tool_registry()
    assert registry.names(AIActionKind.READ) == tuple(tool.name for tool in AI_READ_TOOLS)
    assert registry.names(AIActionKind.WRITE) == tuple(tool.name for tool in AI_WRITE_TOOLS)
    with pytest.raises(KeyError):
        registry.require("unapproved_tool")
    with pytest.raises(ValueError):
        registry.register(AI_READ_TOOLS[0])


def test_registry_lookup_returns_exact_metadata() -> None:
    registry = AIToolRegistry(APPROVED_AI_TOOLS)
    tool = registry.require("global_search")
    assert tool.required_permission == "global_search.view"
    assert "document" in tool.allowed_entities
    assert "permission_denied_without_leakage" in tool.failure_behavior


def test_write_tools_cannot_be_auto_executed_by_registry_contract() -> None:
    for tool in AI_WRITE_TOOLS:
        assert tool.requires_confirmation is True
        assert "business_rules_engine" in tool.business_rule_requirements
        assert "permission_check" in tool.business_rule_requirements
        assert "api_failure_no_success_claim" in tool.failure_behavior
