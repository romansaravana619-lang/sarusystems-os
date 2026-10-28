"""Stable response construction for the AI Company Assistant.

The response contract keeps provider-specific output outside the application
boundary and gives every AI interaction the same machine-readable envelope.
"""

from typing import Any, Iterable
from uuid import UUID

from .contracts import AIRecordReference, AIResponse, AIResponseType


class AIResponseContract:
    """Build validated AI responses without embedding provider logic."""

    @staticmethod
    def answer(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        data: dict[str, Any] | None = None,
        records: Iterable[AIRecordReference] = (),
        recommendations: Iterable[str] = (),
        actions_available: Iterable[str] = (),
        confidence: float | None = None,
        warnings: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.ANSWER,
            summary=summary,
            data=data or {},
            records=list(records),
            recommendations=list(recommendations),
            actions_available=list(actions_available),
            confidence=confidence,
            warnings=list(warnings),
            audit_reference=audit_reference,
        )

    @staticmethod
    def clarification(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        data: dict[str, Any] | None = None,
        actions_available: Iterable[str] = (),
        warnings: Iterable[str] = (),
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.CLARIFICATION,
            summary=summary,
            data=data or {},
            actions_available=list(actions_available),
            warnings=list(warnings),
        )

    @staticmethod
    def action_preview(
        request_id: UUID,
        summary: str,
        *,
        intent: str,
        data: dict[str, Any] | None = None,
        actions_available: Iterable[str] = (),
        warnings: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.ACTION_PREVIEW,
            summary=summary,
            data=data or {},
            actions_available=list(actions_available),
            confirmation_required=True,
            warnings=list(warnings),
            audit_reference=audit_reference,
        )

    @staticmethod
    def action_result(
        request_id: UUID,
        summary: str,
        *,
        intent: str,
        data: dict[str, Any] | None = None,
        records: Iterable[AIRecordReference] = (),
        actions_available: Iterable[str] = (),
        warnings: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.ACTION_RESULT,
            summary=summary,
            data=data or {},
            records=list(records),
            actions_available=list(actions_available),
            warnings=list(warnings),
            audit_reference=audit_reference,
        )

    @staticmethod
    def blocked(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        error_code: str,
        data: dict[str, Any] | None = None,
        actions_available: Iterable[str] = (),
        warnings: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.BLOCKED,
            summary=summary,
            data=data or {},
            actions_available=list(actions_available),
            warnings=list(warnings),
            error_code=error_code,
            audit_reference=audit_reference,
        )

    @staticmethod
    def error(
        request_id: UUID,
        summary: str,
        *,
        intent: str | None = None,
        error_code: str,
        warnings: Iterable[str] = (),
        audit_reference: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request_id=request_id,
            intent=intent,
            response_type=AIResponseType.ERROR,
            summary=summary,
            warnings=list(warnings),
            error_code=error_code,
            audit_reference=audit_reference,
        )


def validate_response(response: AIResponse) -> AIResponse:
    """Re-validate a response at the application boundary."""
    return AIResponse.model_validate(response.model_dump())
