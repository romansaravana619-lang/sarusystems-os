from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.core.database import get_db
from app.projects.models import Deliverable, Milestone, Project, ProjectIssue, ProjectRequirement, ProjectRisk, ProjectScope
from app.projects.schemas import (
    DELIVERABLE_STATUSES, ISSUE_STATUSES, MILESTONE_STATUSES, PROJECT_STATUSES, RISK_STATUSES,
    DeliverableCreate, DeliverableResponse, DeliverableUpdate, IssueCreate, IssueResponse, IssueUpdate,
    MilestoneCreate, MilestoneResponse, MilestoneUpdate, ProjectCreate, ProjectResponse, ProjectUpdate,
    ProjectWorkspaceResponse, RequirementCreate, RequirementResponse, RiskCreate, RiskResponse, RiskUpdate,
    ScopeCreate, ScopeResponse,
)
from app.shared.models import AuditLog, Opportunity, User
from app.tasks.models import Task

router = APIRouter(prefix="/projects", tags=["projects"])

PROJECT_TRANSITIONS = {
    "requirements_pending": {"ready", "on_hold", "cancelled"},
    "ready": {"development", "on_hold", "cancelled"},
    "development": {"testing", "on_hold", "cancelled"},
    "testing": {"review", "development", "on_hold", "cancelled"},
    "review": {"delivery", "testing", "on_hold", "cancelled"},
    "delivery": {"completed", "review", "on_hold"},
    "completed": set(), "on_hold": {"requirements_pending", "ready", "development", "cancelled"}, "cancelled": set(),
}
MILESTONE_TRANSITIONS = {
    "pending": {"active", "in_progress", "on_hold", "cancelled"},
    "planned": {"active", "in_progress", "on_hold", "cancelled"},
    "active": {"in_progress", "review", "delayed", "on_hold", "cancelled"},
    "in_progress": {"review", "delayed", "on_hold", "cancelled"},
    "review": {"completed", "in_progress", "delayed", "on_hold"},
    "delayed": {"active", "in_progress", "review", "on_hold", "cancelled"},
    "on_hold": {"active", "in_progress", "cancelled"},
    "completed": set(), "cancelled": set(),
}
DELIVERABLE_TRANSITIONS = {
    "pending": {"not_submitted", "submitted", "rejected"},
    "not_submitted": {"submitted", "rejected"},
    "submitted": {"in_review", "revision_required", "approved", "rejected"},
    "in_review": {"revision_required", "approved", "rejected"},
    "revision_required": {"submitted", "in_review", "rejected"},
    "rejected": {"revision_required", "submitted"},
    "approved": set(),
}


def _project(db: Session, company_id: UUID, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _owner(db: Session, company_id: UUID, owner_id: UUID | None) -> None:
    if owner_id is None:
        return
    user = db.scalar(select(User).where(User.id == owner_id, User.company_id == company_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=400, detail="Owner must be an active company user.")


def _audit(db: Session, actor: User, action: str, entity: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def _requirements_complete(db: Session, project_id: UUID) -> bool:
    total = db.scalar(select(func.count(ProjectRequirement.id)).where(ProjectRequirement.project_id == project_id)) or 0
    approved = db.scalar(select(func.count(ProjectRequirement.id)).where(ProjectRequirement.project_id == project_id, ProjectRequirement.approved.is_(True))) or 0
    scope = db.scalar(select(ProjectScope.approved).where(ProjectScope.project_id == project_id))
    return total > 0 and total == approved and scope is True


def _validate_transition(db: Session, project: Project, target: str) -> None:
    if target not in PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid project status.")
    if target == project.status:
        return
    if target not in PROJECT_TRANSITIONS.get(project.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid project status transition: {project.status} -> {target}.")
    if target in {"development", "testing", "review", "delivery", "completed"} and not _requirements_complete(db, project.id):
        raise HTTPException(status_code=409, detail="Approved project requirements and an approved project scope are required before delivery execution.")
    if target == "completed":
        open_deliverables = db.scalar(select(func.count(Deliverable.id)).where(Deliverable.project_id == project.id, Deliverable.status != "approved")) or 0
        open_milestones = db.scalar(select(func.count(Milestone.id)).where(Milestone.project_id == project.id, Milestone.status.not_in(["completed", "cancelled"]))) or 0
        open_tasks = db.scalar(select(func.count(Task.id)).where(Task.project_id == project.id, Task.status.not_in(["completed", "cancelled", "done"]))) or 0
        if open_deliverables or open_milestones or open_tasks:
            raise HTTPException(status_code=409, detail="All required tasks, deliverables and milestones must be completed before project completion.")


def _validate_milestone_transition(milestone: Milestone, target: str) -> None:
    if target not in MILESTONE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid milestone status.")
    if target != milestone.status and target not in MILESTONE_TRANSITIONS.get(milestone.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid milestone status transition: {milestone.status} -> {target}.")


def _validate_deliverable_transition(deliverable: Deliverable, target: str) -> None:
    if target not in DELIVERABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid deliverable status.")
    if target != deliverable.status and target not in DELIVERABLE_TRANSITIONS.get(deliverable.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid deliverable status transition: {deliverable.status} -> {target}.")
    if target == "approved" and not deliverable.final_approval:
        raise HTTPException(status_code=409, detail="Final approval must be explicitly recorded before a deliverable is approved.")


@router.get("", response_model=list[ProjectResponse])
def list_projects(current_user: User = Depends(require_permission("projects.view")), db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).where(Project.company_id == current_user.company_id).order_by(Project.created_at.desc())).all())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, current_user: User = Depends(require_permission("projects.create")), db: Session = Depends(get_db)) -> Project:
    opportunity = db.get(Opportunity, payload.opportunity_id)
    if opportunity is None or opportunity.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    if opportunity.stage != "won":
        raise HTTPException(status_code=409, detail="Only won opportunities can create projects.")
    if db.scalar(select(Project).where(Project.opportunity_id == opportunity.id)) is not None:
        raise HTTPException(status_code=409, detail="This won opportunity already has a project.")
    client = db.get(Client, opportunity.id)
    if client is None:
        client = db.scalar(select(Client).where(Client.opportunity_id == opportunity.id))
    if client is None or client.company_id != current_user.company_id:
        raise HTTPException(status_code=409, detail="Won opportunity must have a converted client before project creation.")
    _owner(db, current_user.company_id, payload.owner_user_id)
    project = Project(company_id=current_user.company_id, client_id=client.id, opportunity_id=opportunity.id, owner_user_id=payload.owner_user_id, code="PENDING", name=payload.name, description=payload.description, start_at=payload.start_at, target_end_at=payload.target_end_at, budget=payload.budget, notes=payload.notes)
    db.add(project); db.flush(); project.code = f"PR-{project.id.hex[:8].upper()}"
    _audit(db, current_user, "project.create", "Project", project.id, f"Created from Opportunity {opportunity.id}")
    db.commit(); db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID, current_user: User = Depends(require_permission("projects.view")), db: Session = Depends(get_db)) -> Project:
    return _project(db, current_user.company_id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, payload: ProjectUpdate, current_user: User = Depends(require_permission("projects.edit")), db: Session = Depends(get_db)) -> Project:
    project = _project(db, current_user.company_id, project_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values: _validate_transition(db, project, values["status"])
    if "owner_user_id" in values: _owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items(): setattr(project, key, value)
    _audit(db, current_user, "project.update", "Project", project.id)
    db.commit(); db.refresh(project)
    return project


@router.put("/{project_id}/scope", response_model=ScopeResponse)
def upsert_scope(project_id: UUID, payload: ScopeCreate, current_user: User = Depends(require_permission("projects.scope.edit")), db: Session = Depends(get_db)) -> ProjectScope:
    project = _project(db, current_user.company_id, project_id)
    scope = db.scalar(select(ProjectScope).where(ProjectScope.project_id == project.id))
    if scope is None:
        scope = ProjectScope(project_id=project.id, **payload.model_dump()); db.add(scope)
    else:
        for key, value in payload.model_dump().items(): setattr(scope, key, value)
        scope.approved = False; scope.approved_by_user_id = None; scope.approved_at = None
    db.flush(); _audit(db, current_user, "project.scope.update", "ProjectScope", scope.id)
    db.commit(); db.refresh(scope); return scope


@router.post("/{project_id}/scope/approve", response_model=ScopeResponse)
def approve_scope(project_id: UUID, current_user: User = Depends(require_permission("projects.scope.approve")), db: Session = Depends(get_db)) -> ProjectScope:
    project = _project(db, current_user.company_id, project_id)
    scope = db.scalar(select(ProjectScope).where(ProjectScope.project_id == project.id))
    if scope is None: raise HTTPException(status_code=409, detail="Project scope must exist before approval.")
    scope.approved = True; scope.approved_by_user_id = current_user.id; scope.approved_at = datetime.now(timezone.utc)
    _audit(db, current_user, "project.scope.approve", "ProjectScope", scope.id)
    db.commit(); db.refresh(scope); return scope


@router.get("/{project_id}/requirements", response_model=list[RequirementResponse])
def list_requirements(project_id: UUID, current_user: User = Depends(require_permission("projects.requirements.view")), db: Session = Depends(get_db)) -> list[ProjectRequirement]:
    _project(db, current_user.company_id, project_id)
    return list(db.scalars(select(ProjectRequirement).where(ProjectRequirement.project_id == project_id).order_by(ProjectRequirement.created_at)).all())


@router.post("/{project_id}/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: UUID, payload: RequirementCreate, current_user: User = Depends(require_permission("projects.requirements.create")), db: Session = Depends(get_db)) -> ProjectRequirement:
    _project(db, current_user.company_id, project_id)
    req = ProjectRequirement(project_id=project_id, **payload.model_dump()); db.add(req); db.flush()
    _audit(db, current_user, "project.requirement.create", "ProjectRequirement", req.id)
    db.commit(); db.refresh(req); return req


@router.post("/{project_id}/requirements/{requirement_id}/approve", response_model=RequirementResponse)
def approve_requirement(project_id: UUID, requirement_id: UUID, current_user: User = Depends(require_permission("projects.requirements.approve")), db: Session = Depends(get_db)) -> ProjectRequirement:
    _project(db, current_user.company_id, project_id)
    req = db.scalar(select(ProjectRequirement).where(ProjectRequirement.id == requirement_id, ProjectRequirement.project_id == project_id))
    if req is None: raise HTTPException(status_code=404, detail="Project requirement not found.")
    req.approved = True; req.approved_by_user_id = current_user.id; req.approved_at = datetime.now(timezone.utc)
    _audit(db, current_user, "project.requirement.approve", "ProjectRequirement", req.id)
    db.commit(); db.refresh(req); return req


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
def list_milestones(project_id: UUID, current_user: User = Depends(require_permission("projects.view")), db: Session = Depends(get_db)) -> list[Milestone]:
    _project(db, current_user.company_id, project_id)
    return list(db.scalars(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.sequence)).all())


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
def create_milestone(project_id: UUID, payload: MilestoneCreate, current_user: User = Depends(require_permission("projects.milestones.manage")), db: Session = Depends(get_db)) -> Milestone:
    _project(db, current_user.company_id, project_id)
    milestone = Milestone(project_id=project_id, status="planned", **payload.model_dump()); db.add(milestone); db.flush(); _audit(db, current_user, "project.milestone.create", "Milestone", milestone.id)
    db.commit(); db.refresh(milestone); return milestone


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(milestone_id: UUID, payload: MilestoneUpdate, current_user: User = Depends(require_permission("projects.milestones.manage")), db: Session = Depends(get_db)) -> Milestone:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None: raise HTTPException(status_code=404, detail="Milestone not found.")
    _project(db, current_user.company_id, milestone.project_id)
    values = payload.model_dump(exclude_unset=True)
    target = values.get("status", milestone.status)
    _validate_milestone_transition(milestone, target)
    if target == "completed":
        open_tasks = db.scalar(select(func.count(Task.id)).where(Task.milestone_id == milestone.id, Task.status.not_in(["completed", "cancelled", "done"]))) or 0
        open_deliverables = db.scalar(select(func.count(Deliverable.id)).where(Deliverable.milestone_id == milestone.id, Deliverable.status != "approved")) or 0
        if open_tasks or open_deliverables:
            raise HTTPException(status_code=409, detail="Milestone requires all linked tasks completed and deliverables approved before completion.")
        milestone.completed_at = datetime.now(timezone.utc)
    elif "status" in values:
        milestone.completed_at = None
    for key, value in values.items(): setattr(milestone, key, value)
    _audit(db, current_user, "project.milestone.update", "Milestone", milestone.id)
    db.commit(); db.refresh(milestone); return milestone


@router.get("/{project_id}/deliverables", response_model=list[DeliverableResponse])
def list_deliverables(project_id: UUID, current_user: User = Depends(require_permission("projects.view")), db: Session = Depends(get_db)) -> list[Deliverable]:
    _project(db, current_user.company_id, project_id)
    return list(db.scalars(select(Deliverable).where(Deliverable.project_id == project_id).order_by(Deliverable.created_at)).all())


@router.post("/{project_id}/deliverables", response_model=DeliverableResponse, status_code=status.HTTP_201_CREATED)
def create_deliverable(project_id: UUID, payload: DeliverableCreate, current_user: User = Depends(require_permission("projects.deliverables.manage")), db: Session = Depends(get_db)) -> Deliverable:
    _project(db, current_user.company_id, project_id)
    if payload.milestone_id and db.scalar(select(Milestone.id).where(Milestone.id == payload.milestone_id, Milestone.project_id == project_id)) is None: raise HTTPException(status_code=400, detail="Milestone does not belong to this project.")
    if payload.task_id:
        task = db.get(Task, payload.task_id)
        if task is None or task.company_id != current_user.company_id or task.project_id != project_id: raise HTTPException(status_code=400, detail="Deliverable task must belong to this project.")
    deliverable = Deliverable(project_id=project_id, **payload.model_dump()); db.add(deliverable); db.flush(); _audit(db, current_user, "project.deliverable.create", "Deliverable", deliverable.id)
    db.commit(); db.refresh(deliverable); return deliverable


@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableResponse)
def update_deliverable(deliverable_id: UUID, payload: DeliverableUpdate, current_user: User = Depends(require_permission("projects.deliverables.manage")), db: Session = Depends(get_db)) -> Deliverable:
    deliverable = db.get(Deliverable, deliverable_id)
    if deliverable is None: raise HTTPException(status_code=404, detail="Deliverable not found.")
    _project(db, current_user.company_id, deliverable.project_id)
    values = payload.model_dump(exclude_unset=True)
    target = values.get("status", deliverable.status)
    if target == "not_submitted" and deliverable.status == "pending":
        pass
    _validate_deliverable_transition(deliverable, target)
    milestone_id = values.get("milestone_id", deliverable.milestone_id)
    if milestone_id and db.scalar(select(Milestone.id).where(Milestone.id == milestone_id, Milestone.project_id == deliverable.project_id)) is None: raise HTTPException(status_code=400, detail="Milestone does not belong to this project.")
    if "task_id" in values and values["task_id"]:
        task = db.get(Task, values["task_id"])
        if task is None or task.company_id != current_user.company_id or task.project_id != deliverable.project_id: raise HTTPException(status_code=400, detail="Deliverable task must belong to this project.")
    if target in {"submitted", "in_review", "approved", "rejected", "revision_required"} and not deliverable.acceptance_criteria and not values.get("acceptance_criteria"):
        raise HTTPException(status_code=409, detail="Deliverable acceptance criteria must be defined before review.")
    if target == "submitted":
        deliverable.submitted_at = datetime.now(timezone.utc)
        deliverable.revision_required = False
    if target in {"in_review", "approved", "rejected", "revision_required"}:
        deliverable.reviewed_at = datetime.now(timezone.utc)
    if target == "revision_required":
        deliverable.revision_required = True
        deliverable.final_approval = False
    if target == "approved":
        deliverable.final_approval = True
        deliverable.revision_required = False
    if "final_approval" in values and values["final_approval"] is False and target == "approved":
        raise HTTPException(status_code=409, detail="Approved deliverables require final approval.")
    for key, value in values.items(): setattr(deliverable, key, value)
    _audit(db, current_user, "project.deliverable.update", "Deliverable", deliverable.id)
    db.commit(); db.refresh(deliverable); return deliverable


@router.post("/{project_id}/risks", response_model=RiskResponse, status_code=status.HTTP_201_CREATED)
def create_risk(project_id: UUID, payload: RiskCreate, current_user: User = Depends(require_permission("projects.risks.manage")), db: Session = Depends(get_db)) -> ProjectRisk:
    _project(db, current_user.company_id, project_id); risk = ProjectRisk(project_id=project_id, **payload.model_dump()); db.add(risk); db.flush(); _audit(db, current_user, "project.risk.create", "ProjectRisk", risk.id); db.commit(); db.refresh(risk); return risk


@router.patch("/risks/{risk_id}", response_model=RiskResponse)
def update_risk(risk_id: UUID, payload: RiskUpdate, current_user: User = Depends(require_permission("projects.risks.manage")), db: Session = Depends(get_db)) -> ProjectRisk:
    risk = db.get(ProjectRisk, risk_id)
    if risk is None: raise HTTPException(status_code=404, detail="Project risk not found.")
    _project(db, current_user.company_id, risk.project_id); values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in RISK_STATUSES: raise HTTPException(status_code=400, detail="Invalid risk status.")
    for key, value in values.items(): setattr(risk, key, value)
    _audit(db, current_user, "project.risk.update", "ProjectRisk", risk.id); db.commit(); db.refresh(risk); return risk


@router.post("/{project_id}/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(project_id: UUID, payload: IssueCreate, current_user: User = Depends(require_permission("projects.issues.manage")), db: Session = Depends(get_db)) -> ProjectIssue:
    _project(db, current_user.company_id, project_id); issue = ProjectIssue(project_id=project_id, **payload.model_dump()); db.add(issue); db.flush(); _audit(db, current_user, "project.issue.create", "ProjectIssue", issue.id); db.commit(); db.refresh(issue); return issue


@router.patch("/issues/{issue_id}", response_model=IssueResponse)
def update_issue(issue_id: UUID, payload: IssueUpdate, current_user: User = Depends(require_permission("projects.issues.manage")), db: Session = Depends(get_db)) -> ProjectIssue:
    issue = db.get(ProjectIssue, issue_id)
    if issue is None: raise HTTPException(status_code=404, detail="Project issue not found.")
    _project(db, current_user.company_id, issue.project_id); values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in ISSUE_STATUSES: raise HTTPException(status_code=400, detail="Invalid issue status.")
    for key, value in values.items(): setattr(issue, key, value)
    _audit(db, current_user, "project.issue.update", "ProjectIssue", issue.id); db.commit(); db.refresh(issue); return issue


@router.get("/{project_id}/workspace", response_model=ProjectWorkspaceResponse)
def workspace(project_id: UUID, current_user: User = Depends(require_permission("projects.view")), db: Session = Depends(get_db)) -> ProjectWorkspaceResponse:
    project = _project(db, current_user.company_id, project_id)
    scope = db.scalar(select(ProjectScope).where(ProjectScope.project_id == project.id))
    requirements = list(db.scalars(select(ProjectRequirement).where(ProjectRequirement.project_id == project.id).order_by(ProjectRequirement.created_at)).all())
    milestones = list(db.scalars(select(Milestone).where(Milestone.project_id == project.id).order_by(Milestone.sequence)).all())
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.id).order_by(Task.due_at.is_(None), Task.due_at, Task.created_at.desc())).all())
    deliverables = list(db.scalars(select(Deliverable).where(Deliverable.project_id == project.id).order_by(Deliverable.created_at)).all())
    risks = list(db.scalars(select(ProjectRisk).where(ProjectRisk.project_id == project.id).order_by(ProjectRisk.created_at.desc())).all())
    issues = list(db.scalars(select(ProjectIssue).where(ProjectIssue.project_id == project.id).order_by(ProjectIssue.created_at.desc())).all())
    pending = sum(1 for r in requirements if not r.approved)
    open_risks = sum(1 for r in risks if r.status == "open")
    open_issues = sum(1 for i in issues if i.status not in {"resolved", "closed"})
    total = len(milestones) + len(deliverables)
    completed = sum(1 for m in milestones if m.status == "completed") + sum(1 for d in deliverables if d.status == "approved")
    percent = round(completed * 100 / total) if total else 0
    open_tasks = sum(1 for task in tasks if task.status not in {"completed", "cancelled", "done"})
    completed_tasks = sum(1 for task in tasks if task.status in {"completed", "done"})
    return ProjectWorkspaceResponse(project=project, scope=scope, requirements=requirements, milestones=milestones, tasks=tasks, deliverables=deliverables, risks=risks, issues=issues, open_risks=open_risks, open_issues=open_issues, pending_requirements=pending, open_tasks=open_tasks, completed_tasks=completed_tasks, completion_percent=percent)
