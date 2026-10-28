from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

CLIENT_STATUSES = {"onboarding", "active", "at_risk", "inactive", "archived"}
AGREEMENT_STATUSES = {"draft", "sent", "signed", "expired", "cancelled"}
HEALTH_STATUSES = {"healthy", "watch", "at_risk", "critical"}
ONBOARDING_ITEM_STATUSES = {"pending", "in_progress", "completed", "skipped"}
CLIENT_RELATION_TYPES = {"project", "payment", "communication", "support"}


class ClientCreate(BaseModel):
    opportunity_id: UUID
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=8000)


class ClientUpdate(BaseModel):
    status: str | None = None
    owner_user_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=8000)
    timezone: str | None = Field(default=None, max_length=100)
    preferred_contact_channel: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=8000)


class ClientHealthUpdate(BaseModel):
    health_status: str
    health_score: int = Field(ge=0, le=100)
    health_reason: str | None = Field(default=None, max_length=4000)
    next_health_review_at: datetime | None = None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; opportunity_id: UUID; source_contact_id: UUID; code: str; name: str; company_name: str | None
    email: EmailStr | None; phone: str | None; website: str | None; industry: str | None; address: str | None; timezone: str | None
    preferred_contact_channel: str | None; status: str; owner_user_id: UUID | None; health_status: str; health_score: int
    health_reason: str | None; last_health_reviewed_at: datetime | None; next_health_review_at: datetime | None; notes: str | None
    onboarding_started_at: datetime | None; onboarding_completed_at: datetime | None; created_at: datetime; updated_at: datetime


class ClientContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    role: str | None = Field(default=None, max_length=100)
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=4000)


class ClientContactUpdate(ClientContactCreate):
    pass


class ClientContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; client_id: UUID; name: str; email: EmailStr | None; phone: str | None; role: str | None; is_primary: bool
    notes: str | None; created_at: datetime; updated_at: datetime


class AgreementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: str = "draft"
    document_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)


class AgreementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; client_id: UUID; title: str; status: str; document_id: str | None; notes: str | None; created_at: datetime; updated_at: datetime


class OnboardingItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    required: bool = True
    notes: str | None = Field(default=None, max_length=4000)


class OnboardingItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    required: bool | None = None
    status: str | None = None
    notes: str | None = Field(default=None, max_length=4000)


class OnboardingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; client_id: UUID; title: str; required: bool; status: str; completed_at: datetime | None; notes: str | None
    created_at: datetime; updated_at: datetime


class ClientDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    document_type: str = Field(min_length=1, max_length=100)
    status: str = "active"
    external_document_id: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)


class ClientDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; client_id: UUID; title: str; document_type: str; status: str; external_document_id: str | None; notes: str | None
    created_at: datetime; updated_at: datetime


class ClientRelationCreate(BaseModel):
    relation_type: str
    related_entity_id: UUID
    label: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)
    occurred_at: datetime | None = None


class ClientRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; client_id: UUID; relation_type: str; related_entity_id: UUID; label: str | None; status: str | None; notes: str | None
    occurred_at: datetime | None; created_at: datetime; updated_at: datetime


class ClientWorkspaceResponse(BaseModel):
    client: ClientResponse
    contacts: list[ClientContactResponse]
    agreements: list[AgreementResponse]
    onboarding_items: list[OnboardingItemResponse]
    documents: list[ClientDocumentResponse]
    relations: list[ClientRelationResponse]
    onboarding_required_remaining: int
