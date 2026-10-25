from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PROJECT_STATUSES = {"requirements_pending", "ready", "development", "testing", "review", "delivery", "completed", "on_hold", "cancelled"}
MILESTONE_STATUSES = {"pending", "in_progress", "completed", "on_hold", "cancelled"}
DELIVERABLE_STATUSES = {"pending", "submitted", "in_review", "revision_required", "approved", "rejected"}
RISK_STATUSES = {"open", "mitigated", "closed"}
ISSUE_STATUSES = {"open", "in_progress", "resolved", "closed"}
TASK_STATUSES = {"backlog", "to_do", "in_progress", "blocked", "review", "done", "cancelled"}


class ProjectCreate(BaseModel):
    opportunity_id: UUID
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    owner_user_id: UUID | None = None
    start_at: datetime | None = None
    target_end_at: datetime | None = None
    budget: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    owner_user_id: UUID | None = None
    start_at: datetime | None = None
    target_end_at: datetime | None = None
    budget: float | None = Field(default=None, ge=0)
    notes: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    client_id: UUID
    opportunity_id: UUID
    owner_user_id: UUID | None
    code: str
    name: str
    description: str | None
    status: str
    start_at: datetime | None
    target_end_at: datetime | None
    budget: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ScopeCreate(BaseModel):
    in_scope: str = Field(min_length=1)
    out_of_scope: str | None = None
    assumptions: str | None = None
    exclusions: str | None = None


class ScopeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    in_scope: str
    out_of_scope: str | None
    assumptions: str | None
    exclusions: str | None
    approved: bool
    approved_by_user_id: UUID | None
    approved_at: datetime | None


class RequirementCreate(BaseModel):
    description: str = Field(min_length=1)
    acceptance_criteria: str | None = None
    priority: str = "medium"


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    description: str
    acceptance_criteria: str | None
    priority: str
    approved: bool
    approved_by_user_id: UUID | None
    approved_at: datetime | None


class MilestoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_at: datetime | None = None
    sequence: int = Field(default=1, ge=1)


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = None
    due_at: datetime | None = None
    sequence: int | None = Field(default=None, ge=1)


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    status: str
    due_at: datetime | None
    sequence: int


class DeliverableCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    milestone_id: UUID | None = None


class DeliverableUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    milestone_id: UUID | None = None
    status: str | None = None
    review_notes: str | None = None


class DeliverableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    milestone_id: UUID | None
    title: str
    description: str | None
    status: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    review_notes: str | None


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    severity: str = "medium"
    mitigation: str | None = None


class RiskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    mitigation: str | None = None


class RiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    severity: str
    status: str
    mitigation: str | None


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: str = "medium"


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    resolution: str | None = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    priority: str
    status: str
    resolution: str | None


class ProjectTaskSummary(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    owner_user_id: UUID | None
    due_at: datetime | None


class ProjectWorkspaceResponse(BaseModel):
    project: ProjectResponse
    scope: ScopeResponse | None
    requirements: list[RequirementResponse]
    milestones: list[MilestoneResponse]
    tasks: list[ProjectTaskSummary]
    deliverables: list[DeliverableResponse]
    risks: list[RiskResponse]
    issues: list[IssueResponse]
    open_risks: int
    open_issues: int
    pending_requirements: int
    open_tasks: int
    completed_tasks: int
    completion_percent: int
