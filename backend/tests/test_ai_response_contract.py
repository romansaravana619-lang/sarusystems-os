from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai_assistant import (
    AIRequest,
    AIResponseContract,
    AIResponseType,
    validate_response,
)
from app.ai_assistant.contracts import AIRecordReference


def test_answer_has_stable_machine_readable_envelope() -> None:
    request = AIRequest(message="What needs my attention today?")
    response = AIResponseContract.answer(
        request.request_id,
        "You have 3 items requiring attention.",
        intent="founder_attention",
        data={"count": 3},
        recommendations=["Review overdue tasks"],
        confidence=0.94,
    )

    assert response.request_id == request.request_id
    assert response.response_type == AIResponseType.ANSWER
    assert response.data == {"count": 3}
    assert response.recommendations == ["Review overdue tasks"]
    assert response.confirmation_required is False
    assert validate_response(response) == response


def test_action_preview_always_requires_confirmation() -> None:
    request_id = uuid4()
    response = AIResponseContract.action_preview(
        request_id,
        "Ready to create the follow-up task.",
        intent="create_task",
        data={"title": "Follow up"},
        actions_available=["create_task"],
    )

    assert response.response_type == AIResponseType.ACTION_PREVIEW
    assert response.confirmation_required is True
    assert response.actions_available == ["create_task"]


def test_action_result_supports_records_and_audit_reference() -> None:
    request_id = uuid4()
    record = AIRecordReference(entity_type="task", entity_id=uuid4(), label="Follow up")
    response = AIResponseContract.action_result(
        request_id,
        "Follow-up task created.",
        intent="create_task",
        records=[record],
        audit_reference="audit-123",
    )

    assert response.response_type == AIResponseType.ACTION_RESULT
    assert response.records == [record]
    assert response.audit_reference == "audit-123"
    assert response.confirmation_required is False


def test_blocked_and_error_responses_require_explicit_error_codes() -> None:
    request_id = uuid4()
    blocked = AIResponseContract.blocked(
        request_id,
        "The action is blocked by business rules.",
        intent="assign_freelancer",
        error_code="BUSINESS_RULE_BLOCKED",
    )
    error = AIResponseContract.error(
        request_id,
        "The AI capability failed.",
        error_code="AI_PROVIDER_ERROR",
    )

    assert blocked.response_type == AIResponseType.BLOCKED
    assert blocked.error_code == "BUSINESS_RULE_BLOCKED"
    assert error.response_type == AIResponseType.ERROR
    assert error.error_code == "AI_PROVIDER_ERROR"


def test_response_contract_rejects_invalid_confidence() -> None:
    request_id = uuid4()
    with pytest.raises(ValidationError):
        AIResponseContract.answer(
            request_id,
            "Invalid confidence",
            confidence=1.1,
        )


def test_clarification_preserves_request_and_available_actions() -> None:
    request_id = uuid4()
    response = AIResponseContract.clarification(
        request_id,
        "Which client do you mean?",
        intent="client_lookup",
        actions_available=["search_clients"],
    )

    assert response.request_id == request_id
    assert response.response_type == AIResponseType.CLARIFICATION
    assert response.actions_available == ["search_clients"]
