from uuid import UUID

from pydantic import BaseModel, Field


PRICING_MODELS = {"fixed", "hourly", "monthly", "custom"}


class ServiceCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    pricing_model: str = "custom"
    base_price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    typical_duration_days: int | None = Field(default=None, ge=1)
    required_skills: str | None = None
    freelancer_roles: str | None = None
    workflow_template: str | None = None
    deliverable_template: str | None = None


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    pricing_model: str | None = None
    base_price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    typical_duration_days: int | None = Field(default=None, ge=1)
    required_skills: str | None = None
    freelancer_roles: str | None = None
    workflow_template: str | None = None
    deliverable_template: str | None = None
    is_active: bool | None = None


class ServiceResponse(BaseModel):
    id: UUID
    company_id: UUID
    code: str
    name: str
    category: str | None
    description: str | None
    pricing_model: str
    base_price: float | None
    currency: str
    typical_duration_days: int | None
    required_skills: str | None
    freelancer_roles: str | None
    workflow_template: str | None
    deliverable_template: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ServiceItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_mandatory: bool = True
    sort_order: int = Field(default=0, ge=0)


class ServiceItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_mandatory: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ServiceItemResponse(BaseModel):
    id: UUID
    service_id: UUID
    name: str
    description: str | None
    is_mandatory: bool
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}
