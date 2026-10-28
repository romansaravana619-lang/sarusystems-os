from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WORK_STATUSES = {"assigned", "acknowledged", "in_progress", "submitted", "review", "revision", "approved", "completed", "cancelled"}
REVIEW_DECISIONS = {"approved", "revision"}


class ExecutionCreate(BaseModel):
    task_id: UUID
    assignment_id: UUID


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    assignment_id: UUID
    freelancer_id: UUID
    status: str
    progress_percent: int
    acknowledged_at: datetime | None
    started_at: datetime | None
    submitted_at: datetime | None
    approved_at: datetime | None
    completed_at: datetime | None
    submission_url: str | None
    work_notes: str | None
    created_at: datetime
    updated_at: datetime


class ProgressUpdateCreate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)
    update_text: str = Field(min_length=1, max_length=5000)
    blocker: str | None = None


class ProgressUpdateResponse(ProgressUpdateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    created_by_user_id: UUID
    created_at: datetime


class ReviewCreate(BaseModel):
    decision: str
    feedback: str = Field(min_length=1, max_length=5000)


class ReviewResponse(ReviewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    reviewer_user_id: UUID
    reviewed_at: datetime
    created_at: datetime


class SubmissionCreate(BaseModel):
    submission_url: str | None = None
    work_notes: str | None = None


class WorkLogCreate(BaseModel):
    work_date: datetime
    hours: float = Field(gt=0, le=24)
    description: str = Field(min_length=1, max_length=5000)


class WorkLogResponse(WorkLogCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    created_by_user_id: UUID
    created_at: datetime


class FreelancerWorkWorkspaceResponse(BaseModel):
    total_executions: int
    assigned: int
    acknowledged: int
    in_progress: int
    submitted: int
    review: int
    revision: int
    approved: int
    completed: int
    blocked: int
    executions: list[ExecutionResponse]
