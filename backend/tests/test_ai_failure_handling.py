from uuid import uuid4

import pytest

from app.ai_assistant import AIFailureHandler, AIFailureKind, AIResponseType


def test_failure_kinds_are_explicit():
    assert {item.value for item in AIFailureKind} == {
        "missing_data",
        "multiple_matches",
        "permission_denied",
        "business_rule_blocked",
        "uncertain_intent",
        "os_api_failure",
        "partial_execution_failure",
        "ai_provider_failure",
    }


def test_missing_data_is_blocked_and_lists_fields():
    response = AIFailureHandler.missing_data(
        uuid4(), "Required information is unavailable.", missing_fields=["client_id"]
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == AIFailureKind.MISSING_DATA.value
    assert response.data["missing_fields"] == ["client_id"]


def test_multiple_matches_requires_founder_selection_without_auto_selecting():
    response = AIFailureHandler.multiple_matches(
        uuid4(),
        "Multiple clients matched. Please select the correct client.",
        intent="client_lookup",
        candidate_records=[{"id": "a"}, {"id": "b"}],
    )

    assert response.response_type is AIResponseType.CLARIFICATION
    assert response.error_code is None
    assert response.data["failure_kind"] == "multiple_matches"
    assert len(response.data["candidate_records"]) == 2
    assert response.actions_available == ["select_matching_record"]


def test_multiple_matches_requires_two_or_more_candidates():
    with pytest.raises(ValueError, match="between 2 and 100"):
        AIFailureHandler.multiple_matches(uuid4(), "Ambiguous", candidate_records=[{"id": "a"}])


def test_permission_denied_does_not_expose_protected_permission_details():
    response = AIFailureHandler.permission_denied(
        uuid4(),
        "Internal permission clients.read is required.",
        required_permission="clients.read",
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == "permission_denied"
    assert response.summary == "This information or action is not available to your current account."
    assert "clients.read" not in str(response.model_dump())


def test_business_rule_block_is_preserved_and_can_offer_compliant_next_step():
    response = AIFailureHandler.business_rule_blocked(
        uuid4(),
        "Project requirements must be approved first.",
        rule_code="PROJECT_REQUIREMENTS_APPROVED",
        compliant_next_step="Obtain requirement approval, then retry.",
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == "business_rule_blocked"
    assert response.data["rule_code"] == "PROJECT_REQUIREMENTS_APPROVED"
    assert response.data["compliant_next_step"] == "Obtain requirement approval, then retry."


def test_uncertain_intent_requires_clarification():
    response = AIFailureHandler.uncertain_intent(
        uuid4(),
        "Please clarify what you want to do.",
        candidate_intents=["client_lookup", "client_update"],
    )

    assert response.response_type is AIResponseType.CLARIFICATION
    assert response.data["failure_kind"] == "uncertain_intent"


def test_os_api_failure_is_an_error_and_preserves_retryability_and_audit_reference():
    response = AIFailureHandler.os_api_failure(
        uuid4(),
        "The OS service is temporarily unavailable.",
        service="projects",
        retryable=True,
        audit_reference="audit-123",
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "os_api_failure"
    assert response.data["retryable"] is True
    assert response.data["service"] == "projects"
    assert response.audit_reference == "audit-123"
    assert "not confirmed as successful" in response.warnings[0]


def test_partial_execution_reports_successes_and_failures_without_retry():
    response = AIFailureHandler.partial_execution_failure(
        uuid4(),
        "Two actions completed; one action failed.",
        intent="bulk_update",
        successful_actions=["task-1", "task-2"],
        failed_actions=["task-3"],
        compliant_next_step="Review task-3 and retry it manually if still required.",
        audit_reference="audit-partial-1",
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "partial_execution_failure"
    assert response.data["partial"] is True
    assert response.data["successful_actions"] == ["task-1", "task-2"]
    assert response.data["failed_actions"] == ["task-3"]
    assert response.data["retryable"] is False
    assert response.data["compliant_next_step"].startswith("Review")
    assert response.audit_reference == "audit-partial-1"


def test_partial_execution_requires_both_outcome_lists():
    with pytest.raises(ValueError, match="both successful and failed"):
        AIFailureHandler.partial_execution_failure(
            uuid4(), "Incomplete result", successful_actions=["task-1"], failed_actions=[]
        )


def test_ai_provider_failure_keeps_core_os_available_and_exposes_no_provider_details():
    response = AIFailureHandler.ai_provider_failure(
        uuid4(),
        retryable=True,
        retry_after_seconds=30,
        audit_reference="audit-provider-1",
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "ai_provider_failure"
    assert response.data == {
        "failure_kind": "ai_provider_failure",
        "retryable": True,
        "core_os_available": True,
        "retry_after_seconds": 30,
    }
    assert any("remain available" in warning for warning in response.warnings)
    assert any("No OS action" in warning for warning in response.warnings)
    assert "provider" not in str(response.data)


@pytest.mark.parametrize("retry_after_seconds", [-1, 86_401])
def test_provider_retry_after_is_bounded(retry_after_seconds):
    with pytest.raises(ValueError, match="between 0 and 86400"):
        AIFailureHandler.ai_provider_failure(
            uuid4(), retry_after_seconds=retry_after_seconds
        )


def test_failure_handler_rejects_invalid_request_ids():
    with pytest.raises(ValueError):
        AIFailureHandler.missing_data("not-a-uuid", "invalid")


@pytest.mark.parametrize("values", [[""], ["  "], ["valid"] * 101])
def test_failure_lists_reject_blank_or_oversized_entries(values):
    with pytest.raises(ValueError):
        AIFailureHandler.uncertain_intent(uuid4(), "Clarify", candidate_intents=values)
