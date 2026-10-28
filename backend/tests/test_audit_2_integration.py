from pathlib import Path

from app.ai_assistant.registry import get_default_ai_tool_registry


def test_project_creation_resolves_client_by_opportunity_relationship() -> None:
    source = Path("app/projects/router.py").read_text()
    assert "Client.opportunity_id == opportunity.id" in source
    assert "Client.company_id == current_user.company_id" in source
    assert "db.get(Client, opportunity.id)" not in source


def test_ai_registry_uses_domain_permission_codes() -> None:
    registry = get_default_ai_tool_registry()
    expected = {
        "get_tasks": "tasks.view",
        "get_sales_pipeline": "sales.pipeline.view",
        "get_opportunities": "sales.pipeline.view",
        "get_proposals": "sales.pipeline.view",
        "get_projects": "projects.view",
        "get_project_risks": "projects.view",
        "get_project_milestones": "projects.view",
        "get_unpaid_payments": "finance.dashboard.view",
        "get_financial_summary": "finance.dashboard.view",
        "get_freelancer_workload": "freelancers.view",
        "get_calendar_events": "calendar.view",
        "get_notifications": "notifications.view",
        "get_communication_history": "communication.view",
        "get_client_summary": "clients.view",
        "get_project_summary": "projects.view",
        "get_opportunity_summary": "sales.pipeline.view",
    }
    for tool_name, permission in expected.items():
        assert registry.require(tool_name).required_permission == permission
