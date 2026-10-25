from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


PROSPECT_STATUSES = {"new", "contacted", "qualified", "discovery", "proposal", "won", "lost", "nurture"}
OPPORTUNITY_STAGES = {"qualification", "discovery", "requirement_captured", "proposal", "negotiation", "won", "lost"}


class ProspectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ProspectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    status: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ProspectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    company_name: str | None
    email: EmailStr | None
    phone: str | None
    source: str | None
    status: str
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    prospect_id: UUID | None
    name: str
    company_name: str | None
    email: EmailStr | None
    phone: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OpportunityCreate(BaseModel):
    contact_id: UUID
    name: str = Field(min_length=1, max_length=200)
    service: str | None = Field(default=None, max_length=200)
    stage: str = "qualification"
    estimated_value: float | None = Field(default=None, ge=0)
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    service: str | None = Field(default=None, max_length=200)
    stage: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    contact_id: UUID
    name: str
    service: str | None
    stage: str
    estimated_value: float | None
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
