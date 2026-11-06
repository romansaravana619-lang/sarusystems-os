"""Deterministic, privacy-conscious failure handling for the AI Company Assistant."""

from enum import StrEnum
from typing import Any, Iterable
from uuid import UUID

from .contracts import AIResponse
from .response import AIResponseContract


class AIFailureKind(StrEnum):
    """Failure categories that must remain explicit at the AI boundary."""

    MISSING_DATA = "missing_data"
    MULTIPLE_MATCHES = "multiple_matches"
    PERMISSION_DENIED = "permission_denied"
    BUSINESS_RULE_BLOCKED = "business_rule_blocked"
    UNCERTAIN_INTENT = "uncertain_intent"
    OS_API_FAILURE = "os_api_failure"
    PARTIAL_EXECUTION_FAILURE = "partial_execution_failure"
    AI_PROVIDER_FAILURE = "ai_provider_failure"


class AIFailureHandler:
    """Turn known failure conditions into safe, machine-readable responses."""

    @staticmethod
    def _blocked(
        request_id: UUID,
        *,
        kind: AIFailureKind,
        summary: str,
        intent: str | None = None,
        data: dict[str, Any] | None = None,
        warnings: Iterable[str] = (),
        actions_available: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponseContract.blocked(
            request_id,
            summary,
            intent=intent,
            error_code=kind.value,
            data={"failure_kind": kind.value, **(data or {})},
            warnings=warnings,
            actions_available=actions_available,
            audit_reference=audit_reference,
        )

    @staticmethod
    def _action_labels(values: Iterable[str], *, field_name: str) -> list[str]:
        labels = list(values)
        if len(labels) > 100 or any(not isinstance(value, str) or not value.strip() for value in labels):
            raise ValueError(f"{field_name} must contain at most 100 nonblank strings")
        return labels

    @staticmethod
    def missing_data(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        missing_fields: Iterable[str] = (),
    ) -> AIResponse:
        return AIFailureHandler._blocked(
            request_id,
            kind=AIFailureKind.MISSING_DATA,
            summary=summary,
            intent=intent,
            data={"missing_fields": AIFailureHandler._action_labels(
                missing_fields, field_name="missing_fields"
            )},
        )

    @staticmethod
    def multiple_matches(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        candidate_records: Iterable[Any] = (),
    ) -> AIResponse:
        candidates = list(candidate_records)
        if len(candidates) < 2 or len(candidates) > 100:
            raise ValueError("Multiple-match clarification requires between 2 and 100 candidates")
        return AIResponseContract.clarification(
            request_id,
            summary,
            intent=intent,
            data={
                "failure_kind": AIFailureKind.MULTIPLE_MATCHES.value,
                "candidate_records": candidates,
            },
            actions_available=["select_matching_record"],
        )

    @staticmethod
    def permission_denied(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        required_permission: str | None = None,
    ) -> AIResponse:
        # Deliberately omit permission names and protected-resource details from
        # the founder-facing payload. The argument remains accepted for callers
        # that already pass it, but it is never returned to the user.
        del summary, required_permission
        return AIFailureHandler._blocked(
            request_id,
            kind=AIFailureKind.PERMISSION_DENIED,
            summary="This information or action is not available to your current account.",
            intent=intent,
        )

    @staticmethod
    def business_rule_blocked(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        rule_code: str | None = None,
        compliant_next_step: str | None = None,
    ) -> AIResponse:
        data: dict[str, Any] = {}
        if rule_code is not None:
            data["rule_code"] = rule_code
        if compliant_next_step is not None:
            if not compliant_next_step.strip():
                raise ValueError("compliant_next_step must not be blank")
            data["compliant_next_step"] = compliant_next_step
        return AIFailureHandler._blocked(
            request_id,
            kind=AIFailureKind.BUSINESS_RULE_BLOCKED,
            summary=summary,
            intent=intent,
            data=data,
        )

    @staticmethod
    def uncertain_intent(
        request_id: UUID,
        summary: str,
        *,
        candidate_intents: Iterable[str] = (),
    ) -> AIResponse:
        return AIResponseContract.clarification(
            request_id,
            summary,
            data={
                "failure_kind": AIFailureKind.UNCERTAIN_INTENT.value,
                "candidate_intents": AIFailureHandler._action_labels(
                    candidate_intents, field_name="candidate_intents"
                ),
            },
        )

    @staticmethod
    def os_api_failure(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        service: str | None = None,
        retryable: bool = False,
        audit_reference: str | None = None,
    ) -> AIResponse:
        data: dict[str, Any] = {
            "failure_kind": AIFailureKind.OS_API_FAILURE.value,
            "retryable": retryable,
        }
        if service is not None:
            data["service"] = service
        return AIResponseContract.error(
            request_id,
            summary,
            intent=intent,
            error_code=AIFailureKind.OS_API_FAILURE.value,
            data=data,
            warnings=["The operation was not confirmed as successful."],
            audit_reference=audit_reference,
        )

    @staticmethod
    def partial_execution_failure(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        successful_actions: Iterable[str],
        failed_actions: Iterable[str],
        compliant_next_step: str | None = None,
        audit_reference: str | None = None,
    ) -> AIResponse:
        succeeded = AIFailureHandler._action_labels(
            successful_actions, field_name="successful_actions"
        )
        failed = AIFailureHandler._action_labels(
            failed_actions, field_name="failed_actions"
        )
        if not succeeded or not failed:
            raise ValueError("Partial execution failure requires both successful and failed actions")
        data: dict[str, Any] = {
            "failure_kind": AIFailureKind.PARTIAL_EXECUTION_FAILURE.value,
            "partial": True,
            "successful_actions": succeeded,
            "failed_actions": failed,
            # Never silently replay a partially completed operation.
            "retryable": False,
        }
        if compliant_next_step is not None:
            if not compliant_next_step.strip():
                raise ValueError("compliant_next_step must not be blank")
            data["compliant_next_step"] = compliant_next_step
        return AIResponseContract.error(
            request_id,
            summary,
            intent=intent,
            error_code=AIFailureKind.PARTIAL_EXECUTION_FAILURE.value,
            data=data,
            warnings=[
                "Some actions completed and others failed. Review the result before retrying."
            ],
            audit_reference=audit_reference,
        )

    @staticmethod
    def ai_provider_failure(
        request_id: UUID,
        summary: str = "The AI assistant is temporarily unavailable.",
        *,
        intent: str | None = None,
        retryable: bool = True,
        retry_after_seconds: int | None = None,
        audit_reference: str | None = None,
    ) -> AIResponse:
        if retry_after_seconds is not None and not 0 <= retry_after_seconds <= 86_400:
            raise ValueError("retry_after_seconds must be between 0 and 86400")
        data: dict[str, Any] = {
            "failure_kind": AIFailureKind.AI_PROVIDER_FAILURE.value,
            "retryable": retryable,
            "core_os_available": True,
        }
        if retry_after_seconds is not None:
            data["retry_after_seconds"] = retry_after_seconds
        return AIResponseContract.error(
            request_id,
            summary,
            intent=intent,
            error_code=AIFailureKind.AI_PROVIDER_FAILURE.value,
            data=data,
            warnings=[
                "Core SaruSystems OS operations remain available without the AI assistant.",
                "No OS action was executed by this failed AI request.",
            ],
            audit_reference=audit_reference,
        )
