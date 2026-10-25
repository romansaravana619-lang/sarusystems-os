from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommandCenterUserSummary(BaseModel):
    id: UUID
    full_name: str
    email: str
    is_active: bool
    roles: list[str]


class CommandCenterAuditItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    created_at: datetime


class CommandCenterTaskItem(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    due_at: datetime | None
    owner_user_id: UUID | None
    client_id: UUID | None


class CommandCenterFollowUpItem(BaseModel):
    id: UUID
    name: str
    stage: str
    estimated_value: float | None
    owner_user_id: UUID | None
    updated_at: datetime


class CommandCenterApprovalItem(BaseModel):
    id: UUID
    type: str
    description: str
    reference_id: UUID


class CommandCenterResponse(BaseModel):
    user: CommandCenterUserSummary
    priorities: list[CommandCenterTaskItem]
    follow_ups: list[CommandCenterFollowUpItem]
    approvals: list[CommandCenterApprovalItem]
    deadlines: list[CommandCenterTaskItem]
    business_health: dict[str, int | float]
    alerts: list[CommandCenterTaskItem]
    quick_actions: list[str]
    counts: dict[str, int]
    recent_activity: list[CommandCenterAuditItem]
