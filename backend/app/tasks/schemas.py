from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TASK_STATUSES = {"backlog", "to_do", "in_progress", "blocked", "review", "done", "cancelled"}
TASK_PRIORITIES = {"low", "medium", "high", "urgent"}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    status: str = "backlog"
    priority: str = "medium"
    owner_user_id: UUID | None = None
    client_id: UUID | None = None
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=8000)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    status: str | None = None
    priority: str | None = None
    owner_user_id: UUID | None = None
    client_id: UUID | None = None
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=8000)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    owner_user_id: UUID | None
    client_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ChecklistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class ChecklistUpdate(BaseModel):
    is_completed: bool


class ChecklistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    title: str
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
