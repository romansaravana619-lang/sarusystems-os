from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.core.database import get_db
from app.projects.models import Project
from app.shared.models import AuditLog, User
from app.tasks.models import ChecklistItem, Task
from app.tasks.schemas import (
    ChecklistCreate, ChecklistResponse, ChecklistUpdate, TASK_PRIORITIES, TASK_STATUSES,
    TaskCreate, TaskResponse, TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_STATUS_TRANSITIONS = {
    "backlog": {"to_do", "cancelled"}, "to_do": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"blocked", "review", "cancelled"}, "blocked": {"in_progress", "cancelled"},
    "review": {"in_progress", "done", "cancelled"}, "done": set(), "cancelled": set(),
}


def _task(db: Session, company_id: UUID, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def _validate_status(current: str, target: str) -> None:
    if target not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status.")
    if current != target and target not in TASK_STATUS_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid task status transition: {current} -> {target}.")


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is None:
        return
    owner = db.scalar(select(User).where(User.id == owner_user_id, User.company_id == company_id))
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=400, detail="Task owner must be an active user in the company.")


def _validate_client(db: Session, company_id: UUID, client_id: UUID | None) -> None:
    if client_id is None:
        return
    client = db.get(Client, client_id)
    if client is None or client.company_id != company_id:
        raise HTTPException(status_code=400, detail="Task client must belong to the company.")


def _validate_project(db: Session, company_id: UUID, project_id: UUID | None, client_id: UUID | None) -> None:
    if project_id is None:
        return
    project = db.get(Project, project_id)
    if project is None or project.company_id != company_id:
        raise HTTPException(status_code=400, detail="Task project must belong to the company.")
    if project.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Tasks cannot be added to a completed or cancelled project.")
    if client_id is not None and client_id != project.client_id:
        raise HTTPException(status_code=409, detail="Task client must match the project's client.")


@router.get("", response_model=list[TaskResponse])
def list_tasks(current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.company_id == current_user.company_id).order_by(Task.due_at.is_(None), Task.due_at, Task.created_at.desc())).all())


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, current_user: User = Depends(require_permission("tasks.create")), db: Session = Depends(get_db)) -> Task:
    if payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status.")
    if payload.priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid task priority.")
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    _validate_client(db, current_user.company_id, payload.client_id)
    _validate_project(db, current_user.company_id, payload.project_id, payload.client_id)
    task = Task(company_id=current_user.company_id, **payload.model_dump())
    if task.status == "done":
        task.completed_at = datetime.now(timezone.utc)
    db.add(task); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="task.create", entity_type="Task", entity_id=str(task.id), details=f"Created task {task.title}"))
    db.commit(); db.refresh(task); return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: UUID, payload: TaskUpdate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values: _validate_status(task.status, values["status"])
    if "priority" in values and values["priority"] not in TASK_PRIORITIES: raise HTTPException(status_code=400, detail="Invalid task priority.")
    if "owner_user_id" in values: _validate_owner(db, current_user.company_id, values["owner_user_id"])
    if "client_id" in values: _validate_client(db, current_user.company_id, values["client_id"])
    project_id = values.get("project_id", task.project_id)
    client_id = values.get("client_id", task.client_id)
    _validate_project(db, current_user.company_id, project_id, client_id)
    for key, value in values.items(): setattr(task, key, value)
    if values.get("status") == "done": task.completed_at = datetime.now(timezone.utc)
    elif "status" in values: task.completed_at = None
    db.add(AuditLog(actor_user_id=current_user.id, action="task.update", entity_type="Task", entity_id=str(task.id), details="Updated task fields or lifecycle status"))
    db.commit(); db.refresh(task); return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: UUID, current_user: User = Depends(require_permission("tasks.complete")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_status(task.status, "done")
    task.status = "done"; task.completed_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=current_user.id, action="task.complete", entity_type="Task", entity_id=str(task.id)))
    db.commit(); db.refresh(task); return task


@router.post("/{task_id}/assign", response_model=TaskResponse)
def assign_task(task_id: UUID, owner_user_id: UUID, current_user: User = Depends(require_permission("tasks.assign")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_owner(db, current_user.company_id, owner_user_id)
    task.owner_user_id = owner_user_id
    db.add(AuditLog(actor_user_id=current_user.id, action="task.assign", entity_type="Task", entity_id=str(task.id), details=f"Assigned to {owner_user_id}"))
    db.commit(); db.refresh(task); return task


@router.get("/{task_id}/checklist", response_model=list[ChecklistResponse])
def list_checklist(task_id: UUID, current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[ChecklistItem]:
    _task(db, current_user.company_id, task_id)
    return list(db.scalars(select(ChecklistItem).where(ChecklistItem.task_id == task_id).order_by(ChecklistItem.created_at)).all())


@router.post("/{task_id}/checklist", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def create_checklist_item(task_id: UUID, payload: ChecklistCreate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> ChecklistItem:
    _task(db, current_user.company_id, task_id)
    item = ChecklistItem(task_id=task_id, title=payload.title); db.add(item); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="task.checklist.create", entity_type="ChecklistItem", entity_id=str(item.id), details=f"Task {task_id}"))
    db.commit(); db.refresh(item); return item


@router.patch("/{task_id}/checklist/{item_id}", response_model=ChecklistResponse)
def update_checklist_item(task_id: UUID, item_id: UUID, payload: ChecklistUpdate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> ChecklistItem:
    _task(db, current_user.company_id, task_id)
    item = db.get(ChecklistItem, item_id)
    if item is None or item.task_id != task_id: raise HTTPException(status_code=404, detail="Checklist item not found.")
    item.is_completed = payload.is_completed; item.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
    db.add(AuditLog(actor_user_id=current_user.id, action="task.checklist.update", entity_type="ChecklistItem", entity_id=str(item.id), details=f"Completed={payload.is_completed}"))
    db.commit(); db.refresh(item); return item
