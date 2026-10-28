from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PROSPECT_STATUSES = {"new", "contacted", "responded", "discovery_scheduled", "discovery_completed", "proposal_sent", "negotiation", "won", "lost", "on_hold"}
OPPORTUNITY_STAGES = {"qualification", "discovery", "requirement_captured", "proposal", "negotiation", "won", "lost"}
QUALIFICATION_LEVELS = {"COLD", "WARM", "HOT"}
FOLLOW_UP_STATUSES = {"open", "completed", "cancelled"}

class ProspectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    preferred_channel: str | None = Field(default=None, max_length=50)
    outreach_channel: str | None = Field(default=None, max_length=50)
    problem_observed: str | None = Field(default=None, max_length=2000)
    potential_service: str | None = Field(default=None, max_length=200)
    discovery_angle: str | None = Field(default=None, max_length=2000)
    why_selected: str | None = Field(default=None, max_length=2000)
    lead_score: int = Field(default=0, ge=0, le=100)
    qualification_level: str = "COLD"
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)
    first_contact_at: datetime | None = None
    last_contact_at: datetime | None = None
    follow_up_count: int = Field(default=0, ge=0)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    status: str = "new"

    @field_validator("qualification_level")
    @classmethod
    def validate_qualification(cls, value: str) -> str:
        value = value.upper()
        if value not in QUALIFICATION_LEVELS: raise ValueError("Invalid qualification level.")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in PROSPECT_STATUSES: raise ValueError("Invalid prospect status.")
        return value

class ProspectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    preferred_channel: str | None = Field(default=None, max_length=50)
    outreach_channel: str | None = Field(default=None, max_length=50)
    problem_observed: str | None = Field(default=None, max_length=2000)
    potential_service: str | None = Field(default=None, max_length=200)
    discovery_angle: str | None = Field(default=None, max_length=2000)
    why_selected: str | None = Field(default=None, max_length=2000)
    status: str | None = None
    lead_score: int | None = Field(default=None, ge=0, le=100)
    qualification_level: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)
    first_contact_at: datetime | None = None
    last_contact_at: datetime | None = None
    follow_up_count: int | None = Field(default=None, ge=0)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in PROSPECT_STATUSES: raise ValueError("Invalid prospect status.")
        return value

    @field_validator("qualification_level")
    @classmethod
    def validate_qualification(cls, value: str | None) -> str | None:
        if value is None: return None
        value = value.upper()
        if value not in QUALIFICATION_LEVELS: raise ValueError("Invalid qualification level.")
        return value

class ProspectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; name: str; company_name: str | None; email: EmailStr | None; phone: str | None
    source: str | None; industry: str | None; location: str | None; website: str | None; preferred_channel: str | None
    outreach_channel: str | None; problem_observed: str | None; potential_service: str | None; discovery_angle: str | None; why_selected: str | None
    status: str; lead_score: int; qualification_level: str; owner_user_id: UUID | None; notes: str | None
    first_contact_at: datetime | None; last_contact_at: datetime | None; follow_up_count: int; next_action: str | None; next_action_at: datetime | None
    created_at: datetime; updated_at: datetime

class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200); company_name: str | None = Field(default=None, max_length=200); email: EmailStr | None = None; phone: str | None = Field(default=None, max_length=50); notes: str | None = Field(default=None, max_length=4000)
class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; prospect_id: UUID | None; name: str; company_name: str | None; email: EmailStr | None; phone: str | None; notes: str | None; created_at: datetime; updated_at: datetime
class OpportunityCreate(BaseModel):
    contact_id: UUID; name: str = Field(min_length=1, max_length=200); service: str | None = Field(default=None, max_length=200); stage: str = "qualification"; estimated_value: float | None = Field(default=None, ge=0); owner_user_id: UUID | None = None; notes: str | None = Field(default=None, max_length=4000)
class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200); service: str | None = Field(default=None, max_length=200); stage: str | None = None; estimated_value: float | None = Field(default=None, ge=0); owner_user_id: UUID | None = None; notes: str | None = Field(default=None, max_length=4000)
class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; contact_id: UUID; name: str; service: str | None; stage: str; estimated_value: float | None; owner_user_id: UUID | None; notes: str | None; created_at: datetime; updated_at: datetime
class CommunicationCreate(BaseModel):
    prospect_id: UUID | None = None; contact_id: UUID | None = None; channel: str = Field(min_length=1, max_length=50); direction: str = Field(default="outbound", min_length=1, max_length=20); subject: str | None = Field(default=None, max_length=300); summary: str = Field(min_length=1, max_length=4000); occurred_at: datetime | None = None
class CommunicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; prospect_id: UUID | None; contact_id: UUID | None; channel: str; direction: str; subject: str | None; summary: str; occurred_at: datetime; actor_user_id: UUID | None; created_at: datetime; updated_at: datetime
class FollowUpCreate(BaseModel):
    prospect_id: UUID | None = None; contact_id: UUID | None = None; owner_user_id: UUID; title: str = Field(min_length=1, max_length=300); due_at: datetime; notes: str | None = Field(default=None, max_length=4000)
class FollowUpUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300); due_at: datetime | None = None; status: str | None = None; notes: str | None = Field(default=None, max_length=4000)
class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; prospect_id: UUID | None; contact_id: UUID | None; owner_user_id: UUID; title: str; due_at: datetime; status: str; notes: str | None; completed_at: datetime | None; created_at: datetime; updated_at: datetime
class CRMDashboardResponse(BaseModel):
    total_prospects: int; active_prospects: int; qualified_leads: int; outreach_sent: int; replies: int; positive_replies: int; follow_ups_open: int; follow_ups_overdue: int; discovery_calls: int; proposals: int; negotiations: int; won_opportunities: int; pipeline_value: float; won_value: float; by_prospect_status: dict[str, int]; by_source: dict[str, int]; by_outreach_channel: dict[str, int]; by_opportunity_stage: dict[str, int]
