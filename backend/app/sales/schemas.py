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
    id: UUID; opportunity_id: UUID; summary: str; business_problem: str | None; goals: str | None; notes: str | None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
class RequirementCreate(BaseModel):
    description: str = Field(min_length=1, max_length=8000)
    scope: str | None = Field(default=None, max_length=8000)
    acceptance_criteria: str | None = Field(default=None, max_length=8000)
class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; opportunity_id: UUID; description: str; scope: str | None; acceptance_criteria: str | None; approved: bool; approved_by_user_id: UUID | None; approved_at: datetime | None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
class ProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200); summary: str = Field(min_length=1, max_length=8000); amount: float | None = Field(default=None, ge=0); valid_until: datetime | None = None; notes: str | None = Field(default=None, max_length=4000)
class ProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200); summary: str | None = Field(default=None, min_length=1, max_length=8000); amount: float | None = Field(default=None, ge=0); valid_until: datetime | None = None; notes: str | None = Field(default=None, max_length=4000); status: str | None = None
class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; opportunity_id: UUID; title: str; summary: str; amount: float | None; valid_until: datetime | None; status: str; notes: str | None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
class QuotationCreate(BaseModel):
    quotation_number: str = Field(min_length=1, max_length=50); title: str = Field(min_length=1, max_length=200); subtotal: float = Field(ge=0); tax_amount: float = Field(default=0, ge=0); valid_until: datetime | None = None; notes: str | None = Field(default=None, max_length=4000); proposal_id: UUID | None = None
class QuotationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200); subtotal: float | None = Field(default=None, ge=0); tax_amount: float | None = Field(default=None, ge=0); valid_until: datetime | None = None; notes: str | None = Field(default=None, max_length=4000); status: str | None = None
class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; opportunity_id: UUID; proposal_id: UUID | None; quotation_number: str; title: str; subtotal: float; tax_amount: float; total_amount: float; valid_until: datetime | None; status: str; notes: str | None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
class NegotiationCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=8000); requested_amount: float | None = Field(default=None, ge=0); next_action: str | None = Field(default=None, max_length=500); next_action_at: datetime | None = None; proposal_id: UUID | None = None
class NegotiationUpdate(BaseModel):
    status: str | None = None; summary: str | None = Field(default=None, min_length=1, max_length=8000); requested_amount: float | None = Field(default=None, ge=0); next_action: str | None = Field(default=None, max_length=500); next_action_at: datetime | None = None
class NegotiationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; opportunity_id: UUID; proposal_id: UUID | None; status: str; requested_amount: float | None; summary: str; next_action: str | None; next_action_at: datetime | None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
class DealOutcomeCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=4000); lost_reason: str | None = Field(default=None, max_length=200)
class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    opportunity_id: UUID; outcome: str; lost_reason: str | None; notes: str | None; decided_by_user_id: UUID; decided_at: datetime
class SalesDashboardResponse(BaseModel):
    total_opportunities: int; open_opportunities: int; pipeline_value: float; discovery_count: int; requirement_count: int; proposal_count: int; quotation_count: int; negotiation_count: int; won_count: int; won_value: float; lost_count: int; lost_value: float; conversion_rate: float; by_stage: dict[str, int]; by_lost_reason: dict[str, int]
