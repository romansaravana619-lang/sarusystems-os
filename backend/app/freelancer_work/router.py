from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.freelancers.models import Freelancer, FreelancerAssignment
from app.projects.models import Deliverable
from app.shared.models import AuditLog, User
from app.tasks.models import ChecklistItem, Task, TaskDependency
from app.freelancer_work.models import FreelancerProgressUpdate, FreelancerTaskExecution, FreelancerWorkLog, FreelancerWorkReview
from app.freelancer_work.schemas import (
    ExecutionCreate, ExecutionResponse, FreelancerWorkWorkspaceResponse, ProgressUpdateCreate, ProgressUpdateResponse,
    ReviewCreate, ReviewResponse, SubmissionCreate, WorkLogCreate, WorkLogResponse, REVIEW_DECISIONS, WORK_STATUSES,
)

router = APIRouter(prefix="/freelancer-work", tags=["freelancer-work"])

TRANSITIONS = {
    "assigned": {"acknowledged", "cancelled"},
    "acknowledged": {"in_progress", "cancelled"},
    "in_progress": {"submitted", "cancelled"},
    "submitted": {"review", "cancelled"},
    "review": {"revision", "approved", "cancelled"},
    "revision": {"in_progress", "submitted", "cancelled"},
    "approved": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def _audit(db: Session, actor: User, action: str, entity: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def _execution(db: Session, company_id: UUID, execution_id: UUID) -> FreelancerTaskExecution:
    execution = db.scalar(
        select(FreelancerTaskExecution)
        .join(Task, Task.id == FreelancerTaskExecution.task_id)
        .where(FreelancerTaskExecution.id == execution_id, Task.company_id == company_id)
    )
    if execution is None:
        raise HTTPException(status_code=404, detail="Freelancer work execution not found.")
    return execution


def _task_assignment_context(db: Session, company_id: UUID, task_id: UUID, assignment_id: UUID):
    task = db.get(Task, task_id)
    assignment = db.get(FreelancerAssignment, assignment_id)
    if task is None or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Task not found.")
    if assignment is None:
        raise HTTPException(status_code=404, detail="Freelancer assignment not found.")
    project = db.get(__import__("app.projects.models", fromlist=["Project"]).Project, assignment.project_id)
    if project is None or project.company_id != company_id or task.project_id != assignment.project_id:
        raise HTTPException(status_code=409, detail="Task and freelancer assignment must belong to the same project and company.")
    freelancer = db.get(Freelancer, assignment.freelancer_id)
    if freelancer is None or freelancer.company_id != company_id or freelancer.status != "active":
        raise HTTPException(status_code=409, detail="Only an active freelancer can execute work.")
    if assignment.status not in {"approved", "active"}:
        raise HTTPException(status_code=409, detail="Freelancer assignment must be approved or active before work starts.")
    return task, assignment, freelancer


def _transition(execution: FreelancerTaskExecution, target: str) -> None:
    if target not in WORK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid freelancer work status.")
    if target != execution.status and target not in TRANSITIONS.get(execution.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid freelancer work transition: {execution.status} -> {target}.")


def _validate_task_completion(db: Session, task: Task) -> None:
    if task.status != "review":
        raise HTTPException(status_code=409, detail="The linked task must be in review before freelancer work can be completed.")
    incomplete = db.scalar(select(func.count(ChecklistItem.id)).where(ChecklistItem.task_id == task.id, ChecklistItem.is_completed.is_(False))) or 0
    if incomplete:
        raise HTTPException(status_code=409, detail="All task checklist items must be completed before approval and completion.")
    if task.required_deliverable_id:
        deliverable = db.get(Deliverable, task.required_deliverable_id)
        if deliverable is None or deliverable.status != "approved":
            raise HTTPException(status_code=409, detail="The required deliverable must be approved before freelancer work completion.")
    pending = db.scalar(
        select(func.count(TaskDependency.id))
        .join(Task, Task.id == TaskDependency.depends_on_task_id)
        .where(TaskDependency.task_id == task.id, Task.status.notin_(["completed", "done"]))
    ) or 0
    if pending:
        raise HTTPException(status_code=409, detail="All task dependencies must be completed before freelancer work completion.")


@router.get("/workspace", response_model=FreelancerWorkWorkspaceResponse)
def workspace(current_user: User = Depends(require_permission("freelancer_work.view")), db: Session = Depends(get_db)):
    executions = list(
        db.scalars(
            select(FreelancerTaskExecution)
            .join(Task, Task.id == FreelancerTaskExecution.task_id)
            .where(Task.company_id == current_user.company_id)
            .order_by(FreelancerTaskExecution.created_at.desc())
        ).all()
    )
    return FreelancerWorkWorkspaceResponse(
        total_executions=len(executions),
        assigned=sum(e.status == "assigned" for e in executions),
        acknowledged=sum(e.status == "acknowledged" for e in executions),
        in_progress=sum(e.status == "in_progress" for e in executions),
        submitted=sum(e.status == "submitted" for e in executions),
        review=sum(e.status == "review" for e in executions),
        revision=sum(e.status == "revision" for e in executions),
        approved=sum(e.status == "approved" for e in executions),
        completed=sum(e.status == "completed" for e in executions),
        blocked=sum(1 for e in executions if e.status in {"revision"}),
        executions=executions,
    )


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: UUID, current_user: User = Depends(require_permission("freelancer_work.view")), db: Session = Depends(get_db)):
    return _execution(db, current_user.company_id, execution_id)


@router.post("/executions", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
def create_execution(payload: ExecutionCreate, current_user: User = Depends(require_permission("freelancer_work.assign")), db: Session = Depends(get_db)):
    task, assignment, freelancer = _task_assignment_context(db, current_user.company_id, payload.task_id, payload.assignment_id)
    if task.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Completed or cancelled tasks cannot be assigned for freelancer execution.")
    existing = db.scalar(select(FreelancerTaskExecution.id).where(FreelancerTaskExecution.task_id == task.id))
    if existing:
        raise HTTPException(status_code=409, detail="This task already has a freelancer work execution.")
    execution = FreelancerTaskExecution(task_id=task.id, assignment_id=assignment.id, freelancer_id=freelancer.id, status="assigned")
    db.add(execution); db.flush()
    _audit(db, current_user, "freelancer_work.assign", "FreelancerTaskExecution", execution.id, f"Assigned freelancer {freelancer.id} to task {task.id}")
    db.commit(); db.refresh(execution)
    return execution


@router.post("/executions/{execution_id}/acknowledge", response_model=ExecutionResponse)
def acknowledge(execution_id: UUID, current_user: User = Depends(require_permission("freelancer_work.execute")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id); _transition(execution, "acknowledged")
    execution.status = "acknowledged"; execution.acknowledged_at = datetime.now(timezone.utc)
    _audit(db, current_user, "freelancer_work.acknowledge", "FreelancerTaskExecution", execution.id)
    db.commit(); db.refresh(execution); return execution


@router.post("/executions/{execution_id}/start", response_model=ExecutionResponse)
def start_work(execution_id: UUID, current_user: User = Depends(require_permission("freelancer_work.execute")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id); _transition(execution, "in_progress")
    execution.status = "in_progress"; execution.started_at = datetime.now(timezone.utc)
    _audit(db, current_user, "freelancer_work.start", "FreelancerTaskExecution", execution.id)
    db.commit(); db.refresh(execution); return execution


@router.post("/executions/{execution_id}/progress", response_model=ProgressUpdateResponse, status_code=status.HTTP_201_CREATED)
def progress(execution_id: UUID, payload: ProgressUpdateCreate, current_user: User = Depends(require_permission("freelancer_work.execute")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id)
    if execution.status not in {"acknowledged", "in_progress", "revision"}:
        raise HTTPException(status_code=409, detail="Progress updates are allowed only while work is being executed or revised.")
    execution.progress_percent = payload.progress_percent
    update = FreelancerProgressUpdate(execution_id=execution.id, created_by_user_id=current_user.id, **payload.model_dump())
    db.add(update); db.flush(); _audit(db, current_user, "freelancer_work.progress", "FreelancerProgressUpdate", update.id)
    db.commit(); db.refresh(update); return update


@router.post("/executions/{execution_id}/submit", response_model=ExecutionResponse)
def submit(execution_id: UUID, payload: SubmissionCreate, current_user: User = Depends(require_permission("freelancer_work.execute")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id); _transition(execution, "submitted")
    if execution.progress_percent < 100:
        raise HTTPException(status_code=409, detail="Freelancer work must reach 100 percent before submission.")
    execution.status = "submitted"; execution.submitted_at = datetime.now(timezone.utc)
    execution.submission_url = payload.submission_url; execution.work_notes = payload.work_notes
    _audit(db, current_user, "freelancer_work.submit", "FreelancerTaskExecution", execution.id)
    db.commit(); db.refresh(execution); return execution


@router.post("/executions/{execution_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def review(execution_id: UUID, payload: ReviewCreate, current_user: User = Depends(require_permission("freelancer_work.review")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id); _transition(execution, "review")
    if payload.decision not in REVIEW_DECISIONS:
        raise HTTPException(status_code=400, detail="Review decision must be approved or revision.")
    execution.status = "approved" if payload.decision == "approved" else "revision"
    if payload.decision == "approved": execution.approved_at = datetime.now(timezone.utc)
    review_record = FreelancerWorkReview(execution_id=execution.id, reviewer_user_id=current_user.id, decision=payload.decision, feedback=payload.feedback, reviewed_at=datetime.now(timezone.utc))
    db.add(review_record); db.flush(); _audit(db, current_user, "freelancer_work.review", "FreelancerWorkReview", review_record.id, payload.decision)
    db.commit(); db.refresh(review_record); return review_record


@router.post("/executions/{execution_id}/complete", response_model=ExecutionResponse)
def complete(execution_id: UUID, current_user: User = Depends(require_permission("freelancer_work.complete")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id); _transition(execution, "completed")
    task = db.get(Task, execution.task_id)
    if task is None: raise HTTPException(status_code=404, detail="Linked task not found.")
    _validate_task_completion(db, task)
    task.status = "completed"; task.completed_at = datetime.now(timezone.utc)
    execution.status = "completed"; execution.completed_at = datetime.now(timezone.utc); execution.progress_percent = 100
    _audit(db, current_user, "freelancer_work.complete", "FreelancerTaskExecution", execution.id)
    db.commit(); db.refresh(execution); return execution


@router.post("/executions/{execution_id}/logs", response_model=WorkLogResponse, status_code=status.HTTP_201_CREATED)
def add_work_log(execution_id: UUID, payload: WorkLogCreate, current_user: User = Depends(require_permission("freelancer_work.execute")), db: Session = Depends(get_db)):
    execution = _execution(db, current_user.company_id, execution_id)
    if execution.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Work logs cannot be added to completed or cancelled work.")
    log = FreelancerWorkLog(execution_id=execution.id, created_by_user_id=current_user.id, **payload.model_dump())
    db.add(log); db.flush(); _audit(db, current_user, "freelancer_work.log", "FreelancerWorkLog", log.id)
    db.commit(); db.refresh(log); return log
