from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=8000)
    business_problem: str | None = Field(default=None, max_length=4000)
    goals: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)


class DiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    summary: str
    business_problem: str | None
    goals: str | None
    notes: str | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class RequirementCreate(BaseModel):
    description: str = Field(min_length=1, max_length=8000)
    scope: str | None = Field(default=None, max_length=8000)
    acceptance_criteria: str | None = Field(default=None, max_length=8000)
    approved: bool = False


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    description: str
    scope: str | None
    acceptance_criteria: str | None
    approved: bool
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=8000)
    amount: float | None = Field(default=None, ge=0)
    valid_until: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1, max_length=8000)
    amount: float | None = Field(default=None, ge=0)
    valid_until: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    status: str | None = None


class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    title: str
    summary: str
    amount: float | None
    valid_until: datetime | None
    status: str
    notes: str | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class DealOutcomeCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: UUID
    outcome: str
    notes: str | None
    decided_by_user_id: UUID
    decided_at: datetime
