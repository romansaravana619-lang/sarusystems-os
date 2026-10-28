"""Deterministic failure handling for the AI Company Assistant."""

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
            data={"missing_fields": list(missing_fields)},
        )

    @staticmethod
    def multiple_matches(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        candidate_records: Iterable[Any] = (),
    ) -> AIResponse:
        return AIFailureHandler._blocked(
            request_id,
            kind=AIFailureKind.MULTIPLE_MATCHES,
            summary=summary,
            intent=intent,
            data={"candidate_records": list(candidate_records)},
        )

    @staticmethod
    def permission_denied(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        required_permission: str | None = None,
    ) -> AIResponse:
        data: dict[str, Any] = {}
        if required_permission is not None:
            data["required_permission"] = required_permission
        return AIFailureHandler._blocked(
            request_id,
            kind=AIFailureKind.PERMISSION_DENIED,
            summary=summary,
            intent=intent,
            data=data,
        )

    @staticmethod
    def business_rule_blocked(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        rule_code: str | None = None,
    ) -> AIResponse:
        data: dict[str, Any] = {}
        if rule_code is not None:
            data["rule_code"] = rule_code
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
                "candidate_intents": list(candidate_intents),
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
            audit_reference=audit_reference,
        ).model_copy(update={"data": data})
