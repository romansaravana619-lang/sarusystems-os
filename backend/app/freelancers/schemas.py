from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FREELANCER_STATUSES = {"prospect", "screening", "approved", "onboarding", "active", "inactive", "rejected", "blacklisted"}
APPLICATION_STATUSES = {"received", "screening", "shortlisted", "interview", "selected", "rejected", "withdrawn"}
AGREEMENT_STATUSES = {"draft", "pending_signature", "active", "expired", "terminated"}
ASSIGNMENT_STATUSES = {"proposed", "approved", "active", "paused", "completed", "cancelled"}
AVAILABILITY_STATUSES = {"available", "partially_available", "busy", "unavailable"}

class FreelancerBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: str | None = None
    location: str | None = None
    primary_role: str | None = None
    department: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    portfolio_url: str | None = None
    resume_url: str | None = None
    bio: str | None = None
    rate_type: str = "project"
    rate_amount: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    status: str = "prospect"
    availability_status: str = "available"
    source: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in FREELANCER_STATUSES: raise ValueError("Invalid freelancer status")
        return value

class FreelancerCreate(FreelancerBase): pass
class FreelancerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    primary_role: str | None = None
    department: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    portfolio_url: str | None = None
    resume_url: str | None = None
    bio: str | None = None
    rate_type: str | None = None
    rate_amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    status: str | None = None
    availability_status: str | None = None
    source: str | None = None
    notes: str | None = None

class FreelancerResponse(FreelancerBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_code: str
    company_id: UUID
    created_at: datetime
    updated_at: datetime

class SkillCreate(BaseModel):
    skill: str = Field(min_length=1, max_length=120)
    proficiency: str = "intermediate"
    years: float | None = Field(default=None, ge=0)
class SkillResponse(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_id: UUID

class ApplicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: str | None = None
    role_applied: str | None = None
    source: str | None = None
    portfolio_url: str | None = None
    resume_url: str | None = None
    notes: str | None = None
    status: str = "received"
class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    freelancer_id: UUID | None = None
class ApplicationResponse(ApplicationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    freelancer_id: UUID | None
    created_at: datetime

class EvaluationCreate(BaseModel):
    technical_score: float | None = Field(default=None, ge=0, le=10)
    communication_score: float | None = Field(default=None, ge=0, le=10)
    reliability_score: float | None = Field(default=None, ge=0, le=10)
    portfolio_score: float | None = Field(default=None, ge=0, le=10)
    overall_score: float | None = Field(default=None, ge=0, le=10)
    recommendation: str = "review"
    notes: str | None = None
class EvaluationResponse(EvaluationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    application_id: UUID
    evaluator_user_id: UUID
    created_at: datetime

class AgreementCreate(BaseModel):
    agreement_type: str = "project_based"
    status: str = "draft"
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    document_url: str | None = None
    notes: str | None = None
class AgreementResponse(AgreementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_id: UUID
    created_at: datetime

class AvailabilityCreate(BaseModel):
    status: str = "available"
    available_from: datetime | None = None
    available_until: datetime | None = None
    weekly_hours: float | None = Field(default=None, ge=0)
    notes: str | None = None
class AvailabilityResponse(AvailabilityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_id: UUID
    created_at: datetime

class AssignmentCreate(BaseModel):
    project_id: UUID
    role: str | None = None
    allocation_percent: float = Field(default=100, gt=0, le=100)
    status: str = "proposed"
    start_at: datetime | None = None
    end_at: datetime | None = None
    notes: str | None = None
class AssignmentUpdate(BaseModel):
    role: str | None = None
    allocation_percent: float | None = Field(default=None, gt=0, le=100)
    status: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    notes: str | None = None
class AssignmentResponse(AssignmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_id: UUID
    created_at: datetime

class PerformanceCreate(BaseModel):
    project_id: UUID | None = None
    period: str = Field(min_length=1, max_length=30)
    quality_score: float | None = Field(default=None, ge=0, le=10)
    timeliness_score: float | None = Field(default=None, ge=0, le=10)
    communication_score: float | None = Field(default=None, ge=0, le=10)
    overall_score: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None
class PerformanceResponse(PerformanceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    freelancer_id: UUID
    created_at: datetime

class FreelancerWorkspaceResponse(BaseModel):
    total: int
    active: int
    available: int
    onboarding: int
    screening: int
    inactive: int
    applications: int
    shortlisted_applications: int
    active_assignments: int
    freelancers: list[FreelancerResponse]
