from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    legal_name: str | None
    tagline: str | None
    website: str | None
    email: str | None
    phone: str | None
    address: str | None
    industry: str | None
    business_model: str | None
    vision: str | None
    mission: str | None
    brand_primary_color: str | None
    brand_secondary_color: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompanyProfileUpdate(BaseModel):
    legal_name: str | None = Field(default=None, max_length=250)
    tagline: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    industry: str | None = Field(default=None, max_length=150)
    business_model: str | None = None
    vision: str | None = None
    mission: str | None = None
    brand_primary_color: str | None = Field(default=None, max_length=30)
    brand_secondary_color: str | None = Field(default=None, max_length=30)
    logo_url: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None
    owner_user_id: UUID | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    description: str | None = None
    status: str = "active"
    priority: str = "medium"
    target_date: str | None = None
    owner_user_id: UUID | None = None
    is_active: bool = True


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    target_date: str | None = None
    owner_user_id: UUID | None = None
    is_active: bool | None = None


class GoalResponse(GoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    description: str | None = None
    policy_type: str = Field(default="general", min_length=1, max_length=100)
    status: str = Field(default="active", min_length=1, max_length=50)
    is_active: bool = True


class PolicyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = None
    policy_type: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class PolicyResponse(PolicyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    description: str | None = None
    rule_type: str = Field(default="operating", min_length=1, max_length=100)
    condition: str | None = None
    action: str | None = None
    priority: int = Field(default=100, ge=1, le=10000)
    is_enabled: bool = True


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = None
    rule_type: str | None = Field(default=None, min_length=1, max_length=100)
    condition: str | None = None
    action: str | None = None
    priority: int | None = Field(default=None, ge=1, le=10000)
    is_enabled: bool | None = None


class RuleResponse(RuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyServiceSummary(BaseModel):
    id: UUID
    code: str
    name: str
    category: str | None
    pricing_model: str
    base_price: float | None
    currency: str
    typical_duration_days: int | None
    is_active: bool


class CompanyCoreResponse(BaseModel):
    company: dict
    profile: CompanyProfileResponse
    services: list[CompanyServiceSummary]
    departments: list[DepartmentResponse]
    goals: list[GoalResponse]
    policies: list[PolicyResponse]
    operating_rules: list[RuleResponse]
