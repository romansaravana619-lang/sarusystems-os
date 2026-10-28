from uuid import uuid4

import pytest

from app.ai_assistant.safety import (
    AIConfirmation,
    AISafetyPolicy,
    classify_ai_action,
)


def test_safe_read_is_auto_executable_without_confirmation() -> None:
    decision = classify_ai_action("get_sales_pipeline")
    assert decision.classification == "safe_read"
    assert decision.confirmation_required is False
    assert decision.blocked is False
    AISafetyPolicy().ensure_executable(request_id=uuid4(), action="get_sales_pipeline")


def test_initial_write_actions_require_confirmation() -> None:
    policy = AISafetyPolicy()
    decision = policy.classify("create_followup")
    assert decision.classification == "confirmation_required"
    assert decision.confirmation_required is True
    assert decision.blocked is False

    with pytest.raises(PermissionError, match="explicit_confirmation_required"):
        policy.ensure_executable(request_id=uuid4(), action="create_followup")


def test_confirmation_preview_contains_intended_action_target_fields_and_impact() -> None:
    policy = AISafetyPolicy()
    request_id = uuid4()
    target_id = uuid4()
    preview = policy.preview(
        request_id=request_id,
        action="create_task",
        target_entity_type="project",
        target_entity_id=target_id,
        important_fields={"title": "Follow up with client", "priority": "high"},
        expected_impact="Creates a founder task linked to the project.",
    )

    assert preview.request_id == request_id
    assert preview.action == "create_task"
    assert preview.target_entity_type == "project"
    assert preview.target_entity_id == target_id
    assert preview.important_fields["priority"] == "high"
    assert preview.expected_impact.startswith("Creates")


def test_matching_confirmation_allows_exact_action_only() -> None:
    policy = AISafetyPolicy()
    request_id = uuid4()
    preview = policy.preview(request_id=request_id, action="update_task")
    confirmation = AIConfirmation(
        confirmation_id=preview.confirmation_id,
        request_id=request_id,
        action="update_task",
    )

    policy.ensure_executable(
        request_id=request_id,
        action="update_task",
        preview=preview,
        confirmation=confirmation,
    )


def test_confirmation_cannot_be_replayed_for_different_request_or_action() -> None:
    policy = AISafetyPolicy()
    request_id = uuid4()
    preview = policy.preview(request_id=request_id, action="create_task")
    confirmation = AIConfirmation(
        confirmation_id=preview.confirmation_id,
        request_id=request_id,
        action="create_task",
    )

    with pytest.raises(PermissionError, match="request_mismatch"):
        policy.ensure_executable(
            request_id=uuid4(),
            action="create_task",
            preview=preview,
            confirmation=confirmation,
        )

    with pytest.raises(PermissionError, match="action_mismatch"):
        policy.ensure_executable(
            request_id=request_id,
            action="update_task",
            preview=preview,
            confirmation=confirmation,
        )


def test_wrong_confirmation_id_is_rejected() -> None:
    policy = AISafetyPolicy()
    request_id = uuid4()
    preview = policy.preview(request_id=request_id, action="create_task")
    confirmation = AIConfirmation(
        confirmation_id=uuid4(),
        request_id=request_id,
        action="create_task",
    )

    with pytest.raises(PermissionError, match="confirmation_mismatch"):
        policy.ensure_executable(
            request_id=request_id,
            action="create_task",
            preview=preview,
            confirmation=confirmation,
        )


@pytest.mark.parametrize(
    "action",
    [
        "change_permissions",
        "change_roles",
        "delete_critical_record",
        "execute_payment",
        "send_external_communication",
        "bypass_business_rules",
        "change_security_configuration",
    ],
)
def test_always_blocked_actions_cannot_execute_even_with_confirmation(action: str) -> None:
    policy = AISafetyPolicy()
    decision = policy.classify(action)
    assert decision.blocked is True
    assert decision.confirmation_required is False

    with pytest.raises(PermissionError, match="action_not_permitted"):
        policy.ensure_executable(
            request_id=uuid4(),
            action=action,
            preview=None,
            confirmation=None,
        )


def test_unknown_action_is_fail_closed() -> None:
    decision = classify_ai_action("unknown_action")
    assert decision.blocked is True
    assert decision.reason_code == "unregistered_ai_action"


def test_confirmation_preview_is_not_available_for_safe_reads() -> None:
    with pytest.raises(ValueError, match="only valid"):
        AISafetyPolicy().preview(request_id=uuid4(), action="global_search")
