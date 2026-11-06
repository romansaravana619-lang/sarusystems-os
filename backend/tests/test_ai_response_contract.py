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


def test_response_contract_rejects_blank_summary_and_list_entries() -> None:
    with pytest.raises(ValidationError, match="blank"):
        AIResponseContract.answer(uuid4(), "   ")

    with pytest.raises(ValidationError, match="blank"):
        AIResponseContract.answer(uuid4(), "A valid summary", warnings=["  "])


def test_response_type_invariants_are_enforced_at_model_boundary() -> None:
    request_id = uuid4()

    with pytest.raises(ValidationError, match="must require confirmation"):
        AIResponseContract.answer(request_id, "This is not a preview").model_copy(
            update={
                "response_type": AIResponseType.ACTION_PREVIEW,
                "confirmation_required": False,
            }
        )
        # model_copy does not validate updates; explicit model validation is covered below.

    with pytest.raises(ValidationError, match="must require confirmation"):
        validate_response(
            AIResponseContract.answer(request_id, "A normal answer").model_construct(
                request_id=request_id,
                intent="create_task",
                response_type=AIResponseType.ACTION_PREVIEW,
                summary="Preview",
                data={},
                records=[],
                recommendations=[],
                actions_available=[],
                confirmation_required=False,
                confidence=None,
                warnings=[],
                error_code=None,
                audit_reference=None,
            )
        )


def test_blocked_and_error_models_cannot_omit_error_code() -> None:
    from app.ai_assistant.contracts import AIResponse

    with pytest.raises(ValidationError, match="require an error code"):
        AIResponse(
            request_id=uuid4(),
            response_type=AIResponseType.BLOCKED,
            summary="Blocked by policy",
        )

    with pytest.raises(ValidationError, match="require an error code"):
        AIResponse(
            request_id=uuid4(),
            response_type=AIResponseType.ERROR,
            summary="Provider unavailable",
        )


def test_non_failure_response_cannot_carry_error_code() -> None:
    from app.ai_assistant.contracts import AIResponse

    with pytest.raises(ValidationError, match="only valid"):
        AIResponse(
            request_id=uuid4(),
            response_type=AIResponseType.ANSWER,
            summary="Completed",
            error_code="MISLEADING_ERROR",
        )


def test_action_result_must_identify_the_completed_action() -> None:
    from app.ai_assistant.contracts import AIResponse

    with pytest.raises(ValidationError, match="identify the completed action"):
        AIResponse(
            request_id=uuid4(),
            response_type=AIResponseType.ACTION_RESULT,
            summary="Task created",
        )


def test_response_confidence_rejects_nan_and_infinity() -> None:
    for confidence in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            AIResponseContract.answer(uuid4(), "Confidence must be finite", confidence=confidence)


def test_response_rejects_unknown_fields_and_blank_references() -> None:
    from app.ai_assistant.contracts import AIResponse

    with pytest.raises(ValidationError):
        AIResponse(
            request_id=uuid4(),
            response_type=AIResponseType.ANSWER,
            summary="Answer",
            unexpected="not allowed",
        )

    with pytest.raises(ValidationError, match="blank"):
        AIRecordReference(entity_type="task", entity_id=uuid4(), label="  ")


def test_os_api_failure_keeps_structured_failure_data_inside_contract() -> None:
    from app.ai_assistant import AIFailureHandler

    response = AIFailureHandler.os_api_failure(
        uuid4(),
        "Task service is unavailable.",
        intent="create_task",
        service="task_api",
        retryable=True,
        audit_reference="audit-456",
    )

    assert response.response_type == AIResponseType.ERROR
    assert response.error_code == "os_api_failure"
    assert response.data == {
        "failure_kind": "os_api_failure",
        "retryable": True,
        "service": "task_api",
    }
    assert response.audit_reference == "audit-456"


def test_validate_response_revalidates_untrusted_model_payload() -> None:
    from app.ai_assistant.contracts import AIResponse

    untrusted = AIResponse.model_construct(
        request_id=uuid4(),
        intent=None,
        response_type=AIResponseType.BLOCKED,
        summary="Blocked",
        data={},
        records=[],
        recommendations=[],
        actions_available=[],
        confirmation_required=False,
        confidence=None,
        warnings=[],
        error_code=None,
        audit_reference=None,
    )

    with pytest.raises(ValidationError, match="require an error code"):
        validate_response(untrusted)


def test_all_response_types_have_consistent_envelope_defaults() -> None:
    request_id = uuid4()
    responses = [
        AIResponseContract.answer(request_id, "Answer"),
        AIResponseContract.clarification(request_id, "Please clarify"),
        AIResponseContract.action_preview(request_id, "Review before action", intent="create_task"),
        AIResponseContract.action_result(request_id, "Task created", intent="create_task"),
        AIResponseContract.blocked(request_id, "Action blocked", error_code="BUSINESS_RULE_BLOCKED"),
        AIResponseContract.error(request_id, "Service unavailable", error_code="SERVICE_UNAVAILABLE"),
    ]

    for response in responses:
        validated = validate_response(response)
        assert validated.request_id == request_id
        assert isinstance(validated.data, dict)
        assert isinstance(validated.records, list)
        assert isinstance(validated.recommendations, list)
        assert isinstance(validated.actions_available, list)
        assert isinstance(validated.warnings, list)
