from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


ACTIVITY_TYPES = {"email", "call", "meeting", "client_note", "internal_note", "interaction"}
DIRECTIONS = {"inbound", "outbound", "internal"}
ENTITY_TYPES = {"prospect", "contact", "opportunity", "client", "project", "freelancer", "company"}


class ActivityCreate(BaseModel):
    activity_type: str
    direction: str = "internal"
    subject: str | None = Field(default=None, max_length=300)
    summary: str = Field(min_length=1, max_length=10000)
    occurred_at: datetime
    actor_user_id: UUID | None = None
    client_id: UUID | None = None
    contact_id: UUID | None = None
    prospect_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    freelancer_id: UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = Field(default=None, max_length=100)
    external_reference: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, value: str) -> str:
        if value not in ACTIVITY_TYPES:
            raise ValueError(f"activity_type must be one of {sorted(ACTIVITY_TYPES)}")
        return value

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(DIRECTIONS)}")
        return value

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {sorted(ENTITY_TYPES)}")
        return value


class ActivityUpdate(BaseModel):
    activity_type: str | None = None
    direction: str | None = None
    subject: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, min_length=1, max_length=10000)
    occurred_at: datetime | None = None
    actor_user_id: UUID | None = None
    client_id: UUID | None = None
    contact_id: UUID | None = None
    prospect_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    freelancer_id: UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = Field(default=None, max_length=100)
    external_reference: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=10000)


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    activity_type: str
    direction: str
    subject: str | None
    summary: str
    occurred_at: datetime
    actor_user_id: UUID | None
    client_id: UUID | None
    contact_id: UUID | None
    prospect_id: UUID | None
    opportunity_id: UUID | None
    project_id: UUID | None
    freelancer_id: UUID | None
    entity_type: str | None
    entity_id: str | None
    external_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ActivityDashboard(BaseModel):
    total: int
    emails: int
    calls: int
    meetings: int
    client_notes: int
    internal_notes: int
    interactions: int
