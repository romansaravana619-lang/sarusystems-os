from uuid import uuid4

import pytest

from app.ai_assistant import (
    AIFailureHandler,
    AIFailureKind,
    AIResponseType,
)


def test_failure_kinds_are_explicit():
    assert {item.value for item in AIFailureKind} == {
        "missing_data",
        "multiple_matches",
        "permission_denied",
        "business_rule_blocked",
        "uncertain_intent",
        "os_api_failure",
    }


def test_missing_data_is_blocked_and_lists_fields():
    response = AIFailureHandler.missing_data(
        uuid4(), "More information is required.", missing_fields=["client_id"]
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == AIFailureKind.MISSING_DATA.value
    assert response.data["missing_fields"] == ["client_id"]


def test_multiple_matches_never_selects_a_record():
    response = AIFailureHandler.multiple_matches(
        uuid4(), "Multiple clients matched.", candidate_records=[{"id": "a"}, {"id": "b"}]
    )

    assert response.response_type is AIResponseType.BLOCKED
    assert response.error_code == AIFailureKind.MULTIPLE_MATCHES.value
    assert len(response.data["candidate_records"]) == 2


def test_permission_and_business_rule_failures_are_blocked():
    permission = AIFailureHandler.permission_denied(
        uuid4(), "Permission required.", required_permission="clients.read"
    )
    rule = AIFailureHandler.business_rule_blocked(
        uuid4(), "The operation is not allowed.", rule_code="PROJECT_REQUIREMENTS_APPROVED"
    )

    assert permission.response_type is AIResponseType.BLOCKED
    assert permission.error_code == "permission_denied"
    assert rule.response_type is AIResponseType.BLOCKED
    assert rule.error_code == "business_rule_blocked"


def test_uncertain_intent_requires_clarification():
    response = AIFailureHandler.uncertain_intent(
        uuid4(), "Please clarify what you want to do.", candidate_intents=["client_lookup", "client_update"]
    )

    assert response.response_type is AIResponseType.CLARIFICATION
    assert response.data["failure_kind"] == "uncertain_intent"


def test_os_api_failure_is_an_error_and_preserves_retryability():
    response = AIFailureHandler.os_api_failure(
        uuid4(), "The OS service is temporarily unavailable.", service="projects", retryable=True
    )

    assert response.response_type is AIResponseType.ERROR
    assert response.error_code == "os_api_failure"
    assert response.data["retryable"] is True
    assert response.data["service"] == "projects"


def test_failure_handler_rejects_invalid_request_ids():
    with pytest.raises(ValueError):
        AIFailureHandler.missing_data("not-a-uuid", "invalid")
