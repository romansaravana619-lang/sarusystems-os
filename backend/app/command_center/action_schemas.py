from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FounderActionCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    source_module: str = Field(min_length=1, max_length=100)
    source_entity_id: UUID | None = None
    priority: str = Field(default="medium", min_length=1, max_length=20)
    description: str = Field(min_length=1)
    required_action: str = Field(min_length=1)
    owner_user_id: UUID
    due_date: date | None = None
    founder_notes: str | None = None


class FounderActionUpdate(BaseModel):
    priority: str | None = Field(default=None, min_length=1, max_length=20)
    required_action: str | None = None
    owner_user_id: UUID | None = None
    due_date: date | None = None
    status: str | None = Field(default=None, min_length=1, max_length=30)
    founder_notes: str | None = None
    resolution_date: datetime | None = None


class FounderActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    category: str
    source_module: str
    source_entity_id: UUID | None
    priority: str
    description: str
    required_action: str
    owner_user_id: UUID
    due_date: date | None
    status: str
    founder_notes: str | None
    resolution_date: datetime | None
    created_at: datetime
    updated_at: datetime
