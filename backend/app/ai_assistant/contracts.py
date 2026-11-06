"""Stable contracts for the AI Company Assistant architecture.

These contracts deliberately contain no provider-specific or database logic.
"""

import math
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AIActionKind(StrEnum):
    READ = "read"
    WRITE = "write"


class AIResponseType(StrEnum):
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    ACTION_PREVIEW = "action_preview"
    ACTION_RESULT = "action_result"
    BLOCKED = "blocked"
    ERROR = "error"


class AIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID = Field(default_factory=uuid4)
    message: str = Field(min_length=1, max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)


class AIRecordReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: UUID
    label: str | None = Field(default=None, max_length=500)

    @field_validator("entity_type", "label")
    @classmethod
    def reject_blank_record_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Record reference text must not be blank")
        return value


class AIResponse(BaseModel):
    """The canonical, provider-neutral response envelope returned by AI capabilities."""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    intent: str | None = Field(default=None, min_length=1, max_length=120)
    response_type: AIResponseType
    summary: str = Field(min_length=1, max_length=4000)
    data: dict[str, Any] = Field(default_factory=dict)
    records: list[AIRecordReference] = Field(default_factory=list, max_length=100)
    recommendations: list[str] = Field(default_factory=list, max_length=100)
    actions_available: list[str] = Field(default_factory=list, max_length=100)
    confirmation_required: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    error_code: str | None = Field(default=None, min_length=1, max_length=100)
    audit_reference: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("intent", "summary", "error_code", "audit_reference")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Response text fields must not be blank")
        return value

    @field_validator("confidence")
    @classmethod
    def require_finite_confidence(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Confidence must be a finite number between 0 and 1")
        return value

    @field_validator("recommendations", "actions_available", "warnings")
    @classmethod
    def reject_blank_list_items(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("Response list items must not be blank")
        return values

    @model_validator(mode="after")
    def validate_response_type_rules(self) -> "AIResponse":
        if self.response_type == AIResponseType.ACTION_PREVIEW:
            if not self.confirmation_required:
                raise ValueError("Action preview responses must require confirmation")
            if self.intent is None:
                raise ValueError("Action preview responses must identify the intended action")
        elif self.confirmation_required:
            raise ValueError("Only action preview responses may require confirmation")

        if self.response_type in {AIResponseType.BLOCKED, AIResponseType.ERROR}:
            if self.error_code is None:
                raise ValueError("Blocked and error responses require an error code")
        elif self.error_code is not None:
            raise ValueError("Error codes are only valid for blocked or error responses")

        if self.response_type == AIResponseType.ACTION_RESULT and self.intent is None:
            raise ValueError("Action result responses must identify the completed action")
        return self
