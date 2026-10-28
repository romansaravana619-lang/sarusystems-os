"""Stable contracts for the AI Company Assistant architecture.

These contracts deliberately contain no provider-specific or database logic.
"""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


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


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    intent: str | None = None
    response_type: AIResponseType
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    records: list[AIRecordReference] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    actions_available: list[str] = Field(default_factory=list)
    confirmation_required: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    audit_reference: str | None = None
