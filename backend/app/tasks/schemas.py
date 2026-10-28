from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TASK_STATUSES = {"backlog", "ready", "in_progress", "blocked", "review", "revision", "completed", "cancelled", "done"}
TASK_PRIORITIES = {"critical", "high", "medium", "low", "urgent"}
BLOCKER_STATUSES = {"open", "resolved"}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    expected_output: str | None = Field(default=None, max_length=8000)
    status: str = "backlog"
    priority: str = "medium"
    project_id: UUID | None = None
    product_id: UUID | None = None
    milestone_id: UUID | None = None
    required_deliverable_id: UUID | None = None
    owner_user_id: UUID | None = None
    client_id: UUID | None = None
    start_at: datetime | None = None
    due_at: datetime | None = None
    estimated_hours: float | None = Field(default=None, ge=0)
    founder_notes: str | None = Field(default=None, max_length=8000)
    notes: str | None = Field(default=None, max_length=8000)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    expected_output: str | None = Field(default=None, max_length=8000)
    status: str | None = None
    priority: str | None = None
    project_id: UUID | None = None
    product_id: UUID | None = None
    milestone_id: UUID | None = None
    required_deliverable_id: UUID | None = None
    owner_user_id: UUID | None = None
    client_id: UUID | None = None
    start_at: datetime | None = None
    due_at: datetime | None = None
    estimated_hours: float | None = Field(default=None, ge=0)
    founder_notes: str | None = Field(default=None, max_length=8000)
    notes: str | None = Field(default=None, max_length=8000)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    project_id: UUID | None
    product_id: UUID | None
    milestone_id: UUID | None
    required_deliverable_id: UUID | None
    title: str
    description: str | None
    expected_output: str | None
    status: str
    priority: str
    owner_user_id: UUID | None
    client_id: UUID | None
    start_at: datetime | None
    due_at: datetime | None
    estimated_hours: float | None
    completed_at: datetime | None
    founder_notes: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: UUID
    notes: str | None = Field(default=None, max_length=4000)


class TaskDependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    depends_on_task_id: UUID
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TaskBlockerCreate(BaseModel):
    blocker: str = Field(min_length=1, max_length=8000)
    blocked_by: str | None = Field(default=None, max_length=200)
    required_action: str = Field(min_length=1, max_length=8000)
    owner_user_id: UUID | None = None


class TaskBlockerUpdate(BaseModel):
    blocker: str | None = Field(default=None, min_length=1, max_length=8000)
    blocked_by: str | None = Field(default=None, max_length=200)
    required_action: str | None = Field(default=None, min_length=1, max_length=8000)
    owner_user_id: UUID | None = None
    status: str | None = None
    resolution_date: datetime | None = None


class TaskBlockerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    blocker: str
    blocked_by: str | None
    identified_at: datetime
    required_action: str
    owner_user_id: UUID | None
    resolution_date: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime


class TaskWorkspaceResponse(BaseModel):
    total_tasks: int
    open_tasks: int
    backlog_tasks: int
    ready_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    review_tasks: int
    revision_tasks: int
    completed_tasks: int
    cancelled_tasks: int
    overdue_tasks: int
    unassigned_tasks: int
    critical_tasks: int
    tasks: list[TaskResponse]


class ChecklistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class ChecklistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    is_completed: bool | None = None


class ChecklistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    title: str
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
