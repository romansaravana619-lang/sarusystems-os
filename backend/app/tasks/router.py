from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.core.database import get_db
from app.projects.models import Deliverable, Milestone, Project
from app.products.models import Product
from app.shared.models import AuditLog, User
from app.tasks.models import ChecklistItem, Task, TaskBlocker, TaskDependency
from app.tasks.schemas import (
    BLOCKER_STATUSES,
    TASK_PRIORITIES,
    TASK_STATUSES,
    ChecklistCreate,
    ChecklistResponse,
    ChecklistUpdate,
    TaskBlockerCreate,
    TaskBlockerResponse,
    TaskBlockerUpdate,
    TaskCreate,
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskResponse,
    TaskUpdate,
    TaskWorkspaceResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_STATUS_TRANSITIONS = {
    "backlog": {"ready", "cancelled"},
    "ready": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"blocked", "review", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "review": {"revision", "completed", "cancelled"},
    "revision": {"in_progress", "review", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "done": set(),
}
TERMINAL_STATUSES = {"completed", "cancelled", "done"}
ACTIVE_STATUSES = TASK_STATUSES - TERMINAL_STATUSES - {"backlog"}
EXECUTION_STATUSES = {"in_progress", "review", "revision", "completed", "done"}


def _task(db: Session, company_id: UUID, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def _audit(db: Session, actor: User, action: str, entity_type: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=str(entity_id), details=details))


def _validate_status(current: str, target: str) -> None:
    if target not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status.")
    if current != target and target not in TASK_STATUS_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid task status transition: {current} -> {target}.")


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID | None, *, required: bool = False) -> None:
    if owner_user_id is None:
        if required:
            raise HTTPException(status_code=409, detail="Every active task must have an owner.")
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


def _validate_product(db: Session, company_id: UUID, product_id: UUID | None) -> None:
    if product_id is None:
        return
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id))
    if product is None:
        raise HTTPException(status_code=400, detail="Task product must belong to this company.")
    if product.lifecycle_status in {"deprecated", "archived"}:
        raise HTTPException(status_code=409, detail="Tasks cannot be assigned to a deprecated or archived product.")


def _validate_project_context(
    db: Session,
    company_id: UUID,
    project_id: UUID | None,
    milestone_id: UUID | None,
    deliverable_id: UUID | None,
    client_id: UUID | None,
) -> None:
    if project_id is None and (milestone_id is not None or deliverable_id is not None):
        raise HTTPException(status_code=400, detail="Milestone and deliverable links require a project.")
    if project_id is None:
        return
    project = db.get(Project, project_id)
    if project is None or project.company_id != company_id:
        raise HTTPException(status_code=400, detail="Task project must belong to the company.")
    if project.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Tasks cannot be added to a completed or cancelled project.")
    if client_id is not None and client_id != project.client_id:
        raise HTTPException(status_code=409, detail="Task client must match the project's client.")
    if milestone_id is not None:
        milestone = db.scalar(select(Milestone).where(Milestone.id == milestone_id, Milestone.project_id == project_id))
        if milestone is None:
            raise HTTPException(status_code=400, detail="Task milestone must belong to the project.")
    if deliverable_id is not None:
        deliverable = db.scalar(select(Deliverable).where(Deliverable.id == deliverable_id, Deliverable.project_id == project_id))
        if deliverable is None:
            raise HTTPException(status_code=400, detail="Task deliverable must belong to the project.")
        if milestone_id is not None and deliverable.milestone_id not in {None, milestone_id}:
            raise HTTPException(status_code=409, detail="Task deliverable must match the selected milestone.")


def _validate_blocked(db: Session, task_id: UUID) -> None:
    blockers = db.scalar(select(func.count(TaskBlocker.id)).where(TaskBlocker.task_id == task_id, TaskBlocker.status == "open")) or 0
    if blockers == 0:
        raise HTTPException(status_code=409, detail="A blocked task must have at least one open blocker record.")


def _validate_expected_output(task: Task, target_status: str) -> None:
    if target_status in EXECUTION_STATUSES and not task.expected_output:
        raise HTTPException(status_code=409, detail="Every execution task must have a clear expected output.")


def _validate_dependencies_satisfied(db: Session, task_id: UUID) -> None:
    pending = db.scalar(
        select(func.count(TaskDependency.id))
        .join(Task, Task.id == TaskDependency.depends_on_task_id)
        .where(TaskDependency.task_id == task_id, Task.status != "completed")
        .where(Task.status != "done")
    ) or 0
    if pending:
        raise HTTPException(status_code=409, detail="All task dependencies must be completed before execution can proceed.")


def _validate_completion(db: Session, task: Task) -> None:
    incomplete_checklist = db.scalar(select(func.count(ChecklistItem.id)).where(ChecklistItem.task_id == task.id, ChecklistItem.is_completed.is_(False))) or 0
    if incomplete_checklist:
        raise HTTPException(status_code=409, detail="All checklist items must be completed before task completion.")
    if task.required_deliverable_id is not None:
        deliverable = db.get(Deliverable, task.required_deliverable_id)
        if deliverable is None or deliverable.project_id != task.project_id:
            raise HTTPException(status_code=409, detail="Required deliverable is invalid for this task.")
        if deliverable.status != "approved":
            raise HTTPException(status_code=409, detail="Required deliverable must be approved before task completion.")


def _validate_dependency(db: Session, company_id: UUID, task_id: UUID, depends_on_task_id: UUID) -> None:
    if task_id == depends_on_task_id:
        raise HTTPException(status_code=409, detail="A task cannot depend on itself.")
    dependency_task = _task(db, company_id, depends_on_task_id)
    if dependency_task.status == "cancelled":
        raise HTTPException(status_code=409, detail="A task cannot depend on a cancelled task.")
    existing = db.scalar(select(TaskDependency.id).where(TaskDependency.task_id == task_id, TaskDependency.depends_on_task_id == depends_on_task_id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This task dependency already exists.")

    frontier = [task_id]
    visited: set[UUID] = set()
    while frontier:
        current = frontier.pop()
        if current in visited:
            continue
        visited.add(current)
        parents = db.scalars(select(TaskDependency.task_id).where(TaskDependency.depends_on_task_id == current)).all()
        for parent in parents:
            if parent == depends_on_task_id:
                raise HTTPException(status_code=409, detail="Task dependency would create a circular dependency.")
            frontier.append(parent)


def _active_task_required_owner(task_status: str) -> bool:
    return task_status in ACTIVE_STATUSES


@router.get("", response_model=list[TaskResponse])
def list_tasks(current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.company_id == current_user.company_id).order_by(Task.due_at.is_(None), Task.due_at, Task.created_at.desc())).all())


@router.get("/by-product/{product_id}", response_model=list[TaskResponse])
def list_product_tasks(product_id: UUID, current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[Task]:
    _validate_product(db, current_user.company_id, product_id)
    return list(
        db.scalars(
            select(Task)
            .where(Task.company_id == current_user.company_id, Task.product_id == product_id)
            .order_by(Task.due_at.is_(None), Task.due_at, Task.created_at.desc())
        ).all()
    )


@router.get("/workspace", response_model=TaskWorkspaceResponse)
def task_workspace(current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> TaskWorkspaceResponse:
    tasks = list(db.scalars(select(Task).where(Task.company_id == current_user.company_id).order_by(Task.due_at.is_(None), Task.due_at, Task.created_at.desc())).all())
    now = datetime.now(timezone.utc)
    counts = {status: sum(1 for task in tasks if task.status == status) for status in {"backlog", "ready", "in_progress", "blocked", "review", "revision", "completed", "cancelled"}}
    overdue = sum(1 for task in tasks if task.due_at and task.due_at < now and task.status not in TERMINAL_STATUSES)
    unassigned = sum(1 for task in tasks if task.status not in TERMINAL_STATUSES and task.owner_user_id is None)
    critical = sum(1 for task in tasks if task.priority in {"critical", "urgent"} and task.status not in TERMINAL_STATUSES)
    return TaskWorkspaceResponse(
        total_tasks=len(tasks), open_tasks=sum(1 for task in tasks if task.status not in TERMINAL_STATUSES),
        backlog_tasks=counts["backlog"], ready_tasks=counts["ready"], in_progress_tasks=counts["in_progress"],
        blocked_tasks=counts["blocked"], review_tasks=counts["review"], revision_tasks=counts["revision"],
        completed_tasks=counts["completed"] + counts.get("done", 0), cancelled_tasks=counts["cancelled"],
        overdue_tasks=overdue, unassigned_tasks=unassigned, critical_tasks=critical, tasks=tasks,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, current_user: User = Depends(require_permission("tasks.create")), db: Session = Depends(get_db)) -> Task:
    if payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status.")
    if payload.priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid task priority.")
    if payload.status in {"blocked", "done"}:
        raise HTTPException(status_code=409, detail="Create the task first, then use the task workflow to progress it.")
    _validate_owner(db, current_user.company_id, payload.owner_user_id, required=_active_task_required_owner(payload.status))
    _validate_client(db, current_user.company_id, payload.client_id)
    _validate_product(db, current_user.company_id, payload.product_id)
    _validate_project_context(db, current_user.company_id, payload.project_id, payload.milestone_id, payload.required_deliverable_id, payload.client_id)
    task = Task(company_id=current_user.company_id, **payload.model_dump())
    db.add(task)
    db.flush()
    if task.status == "completed":
        _validate_expected_output(task, task.status)
        _validate_completion(db, task)
        task.completed_at = datetime.now(timezone.utc)
    _audit(db, current_user, "task.create", "Task", task.id, f"Created task {task.title}")
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: UUID, payload: TaskUpdate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    values = payload.model_dump(exclude_unset=True)
    target_status = values.get("status", task.status)
    _validate_status(task.status, target_status)
    if "priority" in values and values["priority"] not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid task priority.")
    if "owner_user_id" in values:
        _validate_owner(db, current_user.company_id, values["owner_user_id"], required=_active_task_required_owner(target_status))
    elif _active_task_required_owner(target_status):
        _validate_owner(db, current_user.company_id, task.owner_user_id, required=True)
    _validate_product(db, current_user.company_id, values.get("product_id", task.product_id))
    project_id = values.get("project_id", task.project_id)
    milestone_id = values.get("milestone_id", task.milestone_id)
    deliverable_id = values.get("required_deliverable_id", task.required_deliverable_id)
    client_id = values.get("client_id", task.client_id)
    _validate_client(db, current_user.company_id, client_id)
    _validate_project_context(db, current_user.company_id, project_id, milestone_id, deliverable_id, client_id)
    if "expected_output" in values and values["expected_output"] is not None and not values["expected_output"].strip():
        raise HTTPException(status_code=400, detail="Expected output cannot be blank.")
    prospective = Task(expected_output=values.get("expected_output", task.expected_output))
    _validate_expected_output(prospective, target_status)
    if target_status in EXECUTION_STATUSES:
        _validate_dependencies_satisfied(db, task.id)
    for key, value in values.items():
        setattr(task, key, value)
    if target_status == "blocked":
        _validate_blocked(db, task.id)
    if target_status == "completed":
        _validate_completion(db, task)
        task.completed_at = datetime.now(timezone.utc)
    elif "status" in values:
        task.completed_at = None
    _audit(db, current_user, "task.update", "Task", task.id, "Updated task fields or lifecycle status")
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/submit", response_model=TaskResponse)
def submit_task(task_id: UUID, current_user: User = Depends(require_permission("tasks.submit")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_status(task.status, "review")
    _validate_owner(db, current_user.company_id, task.owner_user_id, required=True)
    _validate_expected_output(task, "review")
    _validate_dependencies_satisfied(db, task.id)
    task.status = "review"
    _audit(db, current_user, "task.submit", "Task", task.id)
    db.commit(); db.refresh(task)
    return task


@router.post("/{task_id}/request-revision", response_model=TaskResponse)
def request_revision(task_id: UUID, current_user: User = Depends(require_permission("tasks.review")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_status(task.status, "revision")
    task.status = "revision"
    _audit(db, current_user, "task.revision.request", "Task", task.id, "Revision requested after review")
    db.commit(); db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: UUID, current_user: User = Depends(require_permission("tasks.complete")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_status(task.status, "completed")
    _validate_expected_output(task, "completed")
    _validate_dependencies_satisfied(db, task.id)
    _validate_completion(db, task)
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    _audit(db, current_user, "task.complete", "Task", task.id)
    db.commit(); db.refresh(task)
    return task


@router.post("/{task_id}/assign", response_model=TaskResponse)
def assign_task(task_id: UUID, owner_user_id: UUID, current_user: User = Depends(require_permission("tasks.assign")), db: Session = Depends(get_db)) -> Task:
    task = _task(db, current_user.company_id, task_id)
    _validate_owner(db, current_user.company_id, owner_user_id, required=True)
    task.owner_user_id = owner_user_id
    _audit(db, current_user, "task.assign", "Task", task.id, f"Assigned to {owner_user_id}")
    db.commit(); db.refresh(task)
    return task


@router.get("/{task_id}/dependencies", response_model=list[TaskDependencyResponse])
def list_dependencies(task_id: UUID, current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[TaskDependency]:
    _task(db, current_user.company_id, task_id)
    return list(db.scalars(select(TaskDependency).where(TaskDependency.task_id == task_id).order_by(TaskDependency.created_at)).all())


@router.post("/{task_id}/dependencies", response_model=TaskDependencyResponse, status_code=status.HTTP_201_CREATED)
def create_dependency(task_id: UUID, payload: TaskDependencyCreate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> TaskDependency:
    task = _task(db, current_user.company_id, task_id)
    _validate_dependency(db, current_user.company_id, task.id, payload.depends_on_task_id)
    dependency_task = db.get(Task, payload.depends_on_task_id)
    if task.project_id != dependency_task.project_id:
        raise HTTPException(status_code=409, detail="Task dependencies must remain within the same project.")
    dependency = TaskDependency(task_id=task.id, **payload.model_dump())
    db.add(dependency); db.flush()
    _audit(db, current_user, "task.dependency.create", "TaskDependency", dependency.id, f"Task {task.id} depends on {dependency_task.id}")
    db.commit(); db.refresh(dependency)
    return dependency


@router.delete("/{task_id}/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(task_id: UUID, dependency_id: UUID, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> None:
    _task(db, current_user.company_id, task_id)
    dependency = db.scalar(select(TaskDependency).where(TaskDependency.id == dependency_id, TaskDependency.task_id == task_id))
    if dependency is None:
        raise HTTPException(status_code=404, detail="Task dependency not found.")
    db.delete(dependency)
    _audit(db, current_user, "task.dependency.delete", "TaskDependency", dependency.id)
    db.commit()


@router.get("/{task_id}/blockers", response_model=list[TaskBlockerResponse])
def list_blockers(task_id: UUID, current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[TaskBlocker]:
    _task(db, current_user.company_id, task_id)
    return list(db.scalars(select(TaskBlocker).where(TaskBlocker.task_id == task_id).order_by(TaskBlocker.created_at.desc())).all())


@router.post("/{task_id}/blockers", response_model=TaskBlockerResponse, status_code=status.HTTP_201_CREATED)
def create_blocker(task_id: UUID, payload: TaskBlockerCreate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> TaskBlocker:
    task = _task(db, current_user.company_id, task_id)
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    blocker = TaskBlocker(task_id=task.id, identified_at=datetime.now(timezone.utc), **payload.model_dump())
    db.add(blocker); db.flush()
    if task.status in {"backlog", "ready", "in_progress"}:
        task.status = "blocked"
    _audit(db, current_user, "task.blocker.create", "TaskBlocker", blocker.id, f"Task {task.id} blocked")
    db.commit(); db.refresh(blocker)
    return blocker


@router.patch("/{task_id}/blockers/{blocker_id}", response_model=TaskBlockerResponse)
def update_blocker(task_id: UUID, blocker_id: UUID, payload: TaskBlockerUpdate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> TaskBlocker:
    _task(db, current_user.company_id, task_id)
    blocker = db.scalar(select(TaskBlocker).where(TaskBlocker.id == blocker_id, TaskBlocker.task_id == task_id))
    if blocker is None:
        raise HTTPException(status_code=404, detail="Task blocker not found.")
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in BLOCKER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid blocker status.")
    if "owner_user_id" in values:
        _validate_owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items():
        setattr(blocker, key, value)
    if values.get("status") == "resolved" and blocker.resolution_date is None:
        blocker.resolution_date = datetime.now(timezone.utc)
    if blocker.status == "resolved":
        open_count = db.scalar(select(func.count(TaskBlocker.id)).where(TaskBlocker.task_id == task_id, TaskBlocker.status == "open")) or 0
        task = _task(db, current_user.company_id, task_id)
        if open_count == 0 and task.status == "blocked":
            _validate_dependencies_satisfied(db, task.id)
            _validate_expected_output(task, "in_progress")
            task.status = "in_progress"
    _audit(db, current_user, "task.blocker.update", "TaskBlocker", blocker.id)
    db.commit(); db.refresh(blocker)
    return blocker


@router.get("/{task_id}/checklist", response_model=list[ChecklistResponse])
def list_checklist(task_id: UUID, current_user: User = Depends(require_permission("tasks.view")), db: Session = Depends(get_db)) -> list[ChecklistItem]:
    _task(db, current_user.company_id, task_id)
    return list(db.scalars(select(ChecklistItem).where(ChecklistItem.task_id == task_id).order_by(ChecklistItem.created_at)).all())


@router.post("/{task_id}/checklist", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def create_checklist_item(task_id: UUID, payload: ChecklistCreate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> ChecklistItem:
    _task(db, current_user.company_id, task_id)
    item = ChecklistItem(task_id=task_id, title=payload.title)
    db.add(item); db.flush()
    _audit(db, current_user, "task.checklist.create", "ChecklistItem", item.id, f"Task {task_id}")
    db.commit(); db.refresh(item)
    return item


@router.patch("/{task_id}/checklist/{item_id}", response_model=ChecklistResponse)
def update_checklist_item(task_id: UUID, item_id: UUID, payload: ChecklistUpdate, current_user: User = Depends(require_permission("tasks.edit")), db: Session = Depends(get_db)) -> ChecklistItem:
    _task(db, current_user.company_id, task_id)
    item = db.get(ChecklistItem, item_id)
    if item is None or item.task_id != task_id:
        raise HTTPException(status_code=404, detail="Checklist item not found.")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    if "is_completed" in values:
        item.completed_at = datetime.now(timezone.utc) if values["is_completed"] else None
    _audit(db, current_user, "task.checklist.update", "ChecklistItem", item.id, f"Completed={item.is_completed}")
    db.commit(); db.refresh(item)
    return item
