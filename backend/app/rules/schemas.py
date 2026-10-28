from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SOP_STATUSES = {"draft", "active", "paused", "archived"}
RULE_STATUSES = {"draft", "active", "paused", "archived"}
ENFORCEMENT_MODES = {"block", "warn", "info"}


class SOPBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sop_key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=240)
    status: Literal["draft", "active", "paused", "archived"] = "draft"
    purpose: str | None = None
    scope: str | None = None
    owner_user_id: UUID | None = None
    required_roles: list[str] = Field(default_factory=list)
    entry_conditions: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    exit_conditions: dict[str, Any] = Field(default_factory=dict)
    prohibited_actions: list[str] = Field(default_factory=list)
    linked_document_id: UUID | None = None
    notes: str | None = None
    is_enforced: bool = True

    @field_validator("sop_key")
    @classmethod
    def clean_key(cls, value: str) -> str:
        return value.strip()


class SOPCreate(SOPBase):
    pass


class SOPUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=240)
    status: Literal["draft", "active", "paused", "archived"] | None = None
    purpose: str | None = None
    scope: str | None = None
    owner_user_id: UUID | None = None
    required_roles: list[str] | None = None
    entry_conditions: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None
    exit_conditions: dict[str, Any] | None = None
    prohibited_actions: list[str] | None = None
    linked_document_id: UUID | None = None
    notes: str | None = None
    is_enforced: bool | None = None


class SOPResponse(SOPBase):
    id: UUID
    company_id: UUID
    model_config = ConfigDict(from_attributes=True)


class RuleBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=240)
    status: Literal["draft", "active", "paused", "archived"] = "draft"
    trigger_event: str = Field(min_length=2, max_length=120)
    description: str | None = None
    applies_to: str = Field(min_length=2, max_length=100)
    required_conditions: dict[str, Any] = Field(default_factory=dict)
    prohibited_conditions: dict[str, Any] = Field(default_factory=dict)
    required_actions: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_user_ids: list[UUID] = Field(default_factory=list)
    priority: int = Field(default=100, ge=0, le=100000)
    enforcement_mode: Literal["block", "warn", "info"] = "block"
    owner_user_id: UUID | None = None
    reviewer_user_id: UUID | None = None
    notes: str | None = None
    is_enforced: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=240)
    status: Literal["draft", "active", "paused", "archived"] | None = None
    trigger_event: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    applies_to: str | None = Field(default=None, min_length=2, max_length=100)
    required_conditions: dict[str, Any] | None = None
    prohibited_conditions: dict[str, Any] | None = None
    required_actions: list[str] | None = None
    prohibited_actions: list[str] | None = None
    allowed_roles: list[str] | None = None
    allowed_user_ids: list[UUID] | None = None
    priority: int | None = Field(default=None, ge=0, le=100000)
    enforcement_mode: Literal["block", "warn", "info"] | None = None
    owner_user_id: UUID | None = None
    reviewer_user_id: UUID | None = None
    notes: str | None = None
    is_enforced: bool | None = None


class RuleResponse(RuleBase):
    id: UUID
    company_id: UUID
    model_config = ConfigDict(from_attributes=True)


class RuleEvaluateRequest(BaseModel):
    trigger_event: str = Field(min_length=2, max_length=120)
    applies_to: str = Field(min_length=2, max_length=100)
    action: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    user_id: UUID | None = None
    role_names: list[str] = Field(default_factory=list)


class RuleEvaluation(BaseModel):
    rule_id: UUID
    rule_key: str
    name: str
    enforcement_mode: str
    passed: bool
    blocked: bool
    reasons: list[str]


class RuleEvaluateResponse(BaseModel):
    allowed: bool
    evaluations: list[RuleEvaluation]
