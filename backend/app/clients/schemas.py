from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


CLIENT_STATUSES = {"onboarding", "active", "at_risk", "inactive", "archived"}
AGREEMENT_STATUSES = {"draft", "sent", "signed", "expired", "cancelled"}


class ClientCreate(BaseModel):
    opportunity_id: UUID
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=8000)


class ClientUpdate(BaseModel):
    status: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=8000)


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    opportunity_id: UUID
    source_contact_id: UUID
    code: str
    name: str
    company_name: str | None
    email: EmailStr | None
    phone: str | None
    status: str
    owner_user_id: UUID | None
    notes: str | None
    onboarding_started_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ClientContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    role: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)


class ClientContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    name: str
    email: EmailStr | None
    phone: str | None
    role: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AgreementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: str = "draft"
    document_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)


class AgreementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    title: str
    status: str
    document_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
