from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TYPES = {"system_alert", "task_due", "deadline", "meeting_reminder", "follow_up", "payment_due", "payment_received", "approval_required", "project_update", "freelancer_update", "client_update", "workflow_event", "general"}
CHANNELS = {"in_app", "email"}
PRIORITIES = {"low", "normal", "high", "urgent"}
STATUSES = {"unread", "read", "archived", "pending", "sent", "failed"}

class NotificationCreate(BaseModel):
    recipient_user_id: UUID
    notification_type: str
    channel: str = "in_app"
    priority: str = "normal"
    title: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=10000)
    scheduled_for: datetime | None = None
    source_type: str | None = Field(default=None, max_length=80)
    source_id: str | None = Field(default=None, max_length=100)
    action_url: str | None = Field(default=None, max_length=1000)
    payload: dict = Field(default_factory=dict)

    @field_validator("notification_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in TYPES: raise ValueError(f"notification_type must be one of {sorted(TYPES)}")
        return value
    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value: str) -> str:
        if value not in CHANNELS: raise ValueError(f"channel must be one of {sorted(CHANNELS)}")
        return value
    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        if value not in PRIORITIES: raise ValueError(f"priority must be one of {sorted(PRIORITIES)}")
        return value

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; company_id: UUID; recipient_user_id: UUID; notification_type: str; channel: str; priority: str; title: str; message: str; status: str
    scheduled_for: datetime | None; sent_at: datetime | None; read_at: datetime | None; source_type: str | None; source_id: str | None; action_url: str | None; payload: dict; error_message: str | None

class PreferenceUpsert(BaseModel):
    notification_type: str
    channel: str = "in_app"
    enabled: bool = True
    @field_validator("notification_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in TYPES: raise ValueError(f"notification_type must be one of {sorted(TYPES)}")
        return value
    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value: str) -> str:
        if value not in CHANNELS: raise ValueError(f"channel must be one of {sorted(CHANNELS)}")
        return value

class PreferenceResponse(PreferenceUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID

class NotificationDashboard(BaseModel):
    unread: int; high_priority: int; scheduled: int; failed: int; total: int
