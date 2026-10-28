from uuid import uuid4

from app.ai_assistant import AIFailureHandler, AIResponseContract, AIResponseType, validate_response
from app.ai_assistant.contracts import AIRecordReference


def _record(entity_type: str, label: str) -> AIRecordReference:
    return AIRecordReference(entity_type=entity_type, entity_id=uuid4(), label=label)


def test_business_scenario_attention_today_returns_structured_answer():
    request_id = uuid4()
    response = AIResponseContract.answer(
        request_id,
        "There are 3 items requiring attention today.",
        intent="attention_today",
        data={"count": 3},
        records=[_record("task", "Overdue client follow-up")],
        confidence=0.98,
    )

    assert response.request_id == request_id
    assert response.response_type is AIResponseType.ANSWER
    assert response.intent == "attention_today"
    assert response.data["count"] == 3
    assert response.records[0].entity_type == "task"


def test_business_scenario_prospect_follow_up_is_preview_only():
    response = AIResponseContract.action_preview(
        uuid4(),
        "Ready to create a follow-up for the prospect.",
        intent="prospect_follow_up",
        data={"prospect_id": "prospect-1", "channel": "whatsapp"},
        actions_available=["confirm_create_follow_up"],
    )

    assert response.response_type is AIResponseType.ACTION_PREVIEW
    assert response.confirmation_required is True
    assert "confirm_create_follow_up" in response.actions_available


def test_business_scenario_project_risk_is_read_only():
    response = AIResponseContract.answer(
        uuid4(),
        "Project risk is high because two critical tasks are overdue.",
        intent="project_risk",
        data={"risk_level": "high", "overdue_critical_tasks": 2},
    )

    assert response.response_type is AIResponseType.ANSWER
    assert response.confirmation_required is False
    assert response.data["risk_level"] == "high"


def test_business_scenario_unpaid_payments_preserves_records():
    records = [
        _record("payment", "Invoice INV-101 unpaid"),
        _record("payment", "Invoice INV-104 overdue"),
    ]
    response = AIResponseContract.answer(
        uuid4(),
        "2 payments require attention.",
        intent="unpaid_payments",
        data={"count": 2},
        records=records,
    )

    assert response.data["count"] == 2
    assert len(response.records) == 2
    assert {record.entity_type for record in response.records} == {"payment"}


def test_business_scenario_sales_pipeline_returns_structured_summary():
    response = AIResponseContract.answer(
        uuid4(),
        "The active sales pipeline contains 5 opportunities.",
        intent="sales_pipeline",
        data={"opportunity_count": 5, "weighted_value": 125000},
    )

    assert response.response_type is AIResponseType.ANSWER
    assert response.data == {"opportunity_count": 5, "weighted_value": 125000}


def test_business_scenario_follow_up_creation_requires_confirmation():
    response = AIResponseContract.action_preview(
        uuid4(),
        "A follow-up will be created for tomorrow at 10:00.",
        intent="create_follow_up",
        data={"due_at": "10:00", "target_type": "prospect"},
        actions_available=["create_follow_up"],
    )

    assert response.confirmation_required is True
    assert response.response_type is AIResponseType.ACTION_PREVIEW
    assert response.data["target_type"] == "prospect"


def test_business_scenario_ambiguous_request_never_becomes_an_action():
    response = AIFailureHandler.uncertain_intent(
        uuid4(),
        "Please clarify which client you want to update.",
        candidate_intents=["client_lookup", "client_update"],
    )

    assert response.response_type is AIResponseType.CLARIFICATION
    assert response.confirmation_required is False
    assert response.actions_available == []
    assert response.data["failure_kind"] == "uncertain_intent"


def test_business_scenario_permission_denial_blocks_the_operation():
    response = AIFailureHandler.permission_denied(
        uuid4(),
        "You do not have permission to perform this operation.",
        intent="client_update",
        required_permission="clients.write",
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == "permission_denied"
    assert response.actions_available == []
    assert response.data["required_permission"] == "clients.write"


def test_business_scenario_business_rule_block_stays_blocked():
    response = AIFailureHandler.business_rule_blocked(
        uuid4(),
        "The operation is blocked by an active business rule.",
        intent="project_start",
        rule_code="PROJECT_REQUIREMENTS_APPROVED",
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == "business_rule_blocked"
    assert response.data["rule_code"] == "PROJECT_REQUIREMENTS_APPROVED"


def test_business_scenario_os_api_failure_does_not_become_a_success():
    response = AIFailureHandler.os_api_failure(
        uuid4(),
        "The project service is temporarily unavailable.",
        intent="project_risk",
        service="projects",
        retryable=True,
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "os_api_failure"
    assert response.data["retryable"] is True
    assert response.data["service"] == "projects"


def test_business_scenario_company_scoped_response_keeps_only_active_company_data():
    active_company_id = "company-a"
    response = AIResponseContract.answer(
        uuid4(),
        "2 opportunities found for the active company.",
        intent="sales_pipeline",
        data={"company_id": active_company_id, "opportunity_count": 2},
    )

    assert response.data["company_id"] == active_company_id
    assert response.data["opportunity_count"] == 2
    assert "company-b" not in response.model_dump_json()


def test_regression_response_contract_remains_valid_after_failure_handling():
    response = AIResponseContract.answer(
        uuid4(),
        "Regression check passed.",
        intent="regression_check",
        data={"status": "ok"},
        confidence=1.0,
    )

    validated = validate_response(response)

    assert validated == response
    assert validated.response_type is AIResponseType.ANSWER
    assert validated.data["status"] == "ok"
