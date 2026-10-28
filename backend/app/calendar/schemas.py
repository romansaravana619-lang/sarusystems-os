from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVENT_TYPES = {"discovery_call", "client_meeting", "freelancer_meeting", "deadline", "content_schedule", "follow_up", "founder_reminder", "other"}
STATUSES = {"scheduled", "completed", "cancelled", "rescheduled"}
ENTITY_TYPES = {"prospect", "contact", "opportunity", "client", "project", "freelancer", "task", "company"}


class ReminderCreate(BaseModel):
    minutes_before: int = Field(ge=0, le=43200)


class ReminderResponse(ReminderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    remind_at: datetime
    status: str
    delivered_at: datetime | None = None


class CalendarEventCreate(BaseModel):
    event_type: str
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    status: str = "scheduled"
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=500)
    meeting_url: str | None = Field(default=None, max_length=1000)
    owner_user_id: UUID | None = None
    attendees: list[str] = Field(default_factory=list, max_length=100)
    client_id: UUID | None = None
    contact_id: UUID | None = None
    prospect_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    freelancer_id: UUID | None = None
    task_id: UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10000)
    reminders: list[ReminderCreate] = Field(default_factory=list, max_length=10)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {sorted(EVENT_TYPES)}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in STATUSES:
            raise ValueError(f"status must be one of {sorted(STATUSES)}")
        return value

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {sorted(ENTITY_TYPES)}")
        return value

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError("entity_type and entity_id must be provided together")
        return self


class CalendarEventUpdate(BaseModel):
    event_type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    status: str | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=500)
    meeting_url: str | None = Field(default=None, max_length=1000)
    owner_user_id: UUID | None = None
    attendees: list[str] | None = Field(default=None, max_length=100)
    client_id: UUID | None = None
    contact_id: UUID | None = None
    prospect_id: UUID | None = None
    opportunity_id: UUID | None = None
    project_id: UUID | None = None
    freelancer_id: UUID | None = None
    task_id: UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str | None) -> str | None:
        if value is not None and value not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {sorted(EVENT_TYPES)}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in STATUSES:
            raise ValueError(f"status must be one of {sorted(STATUSES)}")
        return value

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {sorted(ENTITY_TYPES)}")
        return value


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    event_type: str
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    all_day: bool
    status: str
    timezone: str
    location: str | None
    meeting_url: str | None
    owner_user_id: UUID
    attendees: list[str]
    client_id: UUID | None
    contact_id: UUID | None
    prospect_id: UUID | None
    opportunity_id: UUID | None
    project_id: UUID | None
    freelancer_id: UUID | None
    task_id: UUID | None
    entity_type: str | None
    entity_id: str | None
    notes: str | None
    reminders: list[ReminderResponse] = Field(default_factory=list)


class CalendarDashboard(BaseModel):
    total_upcoming: int
    today: int
    discovery_calls: int
    client_meetings: int
    freelancer_meetings: int
    deadlines: int
    content_schedule: int
    follow_ups: int
    founder_reminders: int
    overdue: int
