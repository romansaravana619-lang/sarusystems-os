from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.command_center.action_schemas import FounderActionCreate, FounderActionResponse, FounderActionUpdate
from app.command_center.models import FounderAction
from app.command_center.schemas import (
    CommandCenterApprovalItem,
    CommandCenterAuditItem,
    CommandCenterFounderActionItem,
    CommandCenterFollowUpItem,
    CommandCenterResponse,
    CommandCenterTaskItem,
    CommandCenterUserSummary,
)
from app.core.database import get_db
from app.sales.models import Requirement
from app.shared.models import AuditLog, Opportunity, Permission, Role, User
from app.tasks.models import Task

router = APIRouter(prefix="/command-center", tags=["command-center"])

OPEN_TASK_STATUSES = {"backlog", "to_do", "in_progress", "blocked", "review"}
OPEN_OPPORTUNITY_STAGES = {"qualification", "discovery", "requirement_captured", "proposal", "negotiation"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
VALID_ACTION_STATUSES = {"open", "in_progress", "done", "cancelled"}
VALID_PRIORITIES = set(PRIORITY_ORDER)


def _task_item(task: Task) -> CommandCenterTaskItem:
    return CommandCenterTaskItem(
        id=task.id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        due_at=task.due_at,
        owner_user_id=task.owner_user_id,
        client_id=task.client_id,
    )


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID) -> None:
    owner = db.scalar(select(User).where(User.id == owner_user_id, User.company_id == company_id, User.is_active.is_(True)))
    if owner is None:
        raise HTTPException(status_code=400, detail="Owner must be an active user in the company.")


def _action_item(action: FounderAction) -> CommandCenterFounderActionItem:
    return CommandCenterFounderActionItem(
        id=action.id,
        category=action.category,
        source_module=action.source_module,
        source_entity_id=action.source_entity_id,
        priority=action.priority,
        description=action.description,
        required_action=action.required_action,
        owner_user_id=action.owner_user_id,
        due_date=action.due_date,
        status=action.status,
        founder_notes=action.founder_notes,
        resolution_date=action.resolution_date,
    )


@router.get("", response_model=CommandCenterResponse)
def get_command_center(
    current_user: User = Depends(require_permission("command_center.view")),
    db: Session = Depends(get_db),
) -> CommandCenterResponse:
    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == current_user.id))
    if user is None:
        raise HTTPException(status_code=404, detail="Authenticated user was not found")

    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)
    next_week = today_start + timedelta(days=7)

    tasks = list(
        db.scalars(
            select(Task)
            .where(Task.company_id == user.company_id, Task.status.in_(OPEN_TASK_STATUSES))
            .order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
            .limit(100)
        ).all()
    )
    priorities = sorted(
        [task for task in tasks if task.due_at is not None and task.due_at < tomorrow_start],
        key=lambda task: (PRIORITY_ORDER.get(task.priority.lower(), 9), task.due_at or now),
    )[:10]
    deadlines = [task for task in tasks if task.due_at is not None and now <= task.due_at < next_week][:10]
    alerts = [task for task in tasks if task.status == "blocked" or (task.due_at is not None and task.due_at < now)][:10]

    opportunities = list(
        db.scalars(
            select(Opportunity)
            .where(Opportunity.company_id == user.company_id, Opportunity.stage.in_(OPEN_OPPORTUNITY_STAGES))
            .order_by(Opportunity.updated_at.desc())
            .limit(10)
        ).all()
    )
    follow_ups = [
        CommandCenterFollowUpItem(
            id=opportunity.id,
            name=opportunity.name,
            stage=opportunity.stage,
            estimated_value=float(opportunity.estimated_value) if opportunity.estimated_value is not None else None,
            owner_user_id=opportunity.owner_user_id,
            updated_at=opportunity.updated_at,
        )
        for opportunity in opportunities
    ]

    pending_requirements = list(
        db.scalars(
            select(Requirement)
            .join(Opportunity, Requirement.opportunity_id == Opportunity.id)
            .where(
                Opportunity.company_id == user.company_id,
                Requirement.approved.is_(False),
                Opportunity.stage.in_({"requirement_captured", "proposal"}),
            )
            .order_by(Requirement.created_at.asc())
            .limit(10)
        ).all()
    )
    approvals = [
        CommandCenterApprovalItem(id=requirement.id, type="requirement", description=requirement.description, reference_id=requirement.opportunity_id)
        for requirement in pending_requirements
    ]

    founder_actions = list(
        db.scalars(
            select(FounderAction)
            .where(FounderAction.company_id == user.company_id, FounderAction.status.in_({"open", "in_progress"}))
            .order_by(FounderAction.due_date.asc().nullslast(), FounderAction.created_at.desc())
            .limit(20)
        ).all()
    )

    user_count = db.scalar(select(func.count(User.id)).where(User.company_id == user.company_id)) or 0
    active_user_count = db.scalar(select(func.count(User.id)).where(User.company_id == user.company_id, User.is_active.is_(True))) or 0
    inactive_user_count = user_count - active_user_count
    role_count = db.scalar(select(func.count(Role.id)).where(Role.is_active.is_(True))) or 0
    permission_count = db.scalar(select(func.count(Permission.id))) or 0
    active_client_count = db.scalar(select(func.count(Client.id)).where(Client.company_id == user.company_id, Client.status != "closed")) or 0
    open_opportunity_count = len(opportunities)
    pipeline_value = db.scalar(
        select(func.coalesce(func.sum(Opportunity.estimated_value), 0)).where(
            Opportunity.company_id == user.company_id,
            Opportunity.stage.in_(OPEN_OPPORTUNITY_STAGES),
        )
    ) or 0
    overdue_count = sum(1 for task in tasks if task.due_at is not None and task.due_at < now)
    blocked_count = sum(1 for task in tasks if task.status == "blocked")

    recent_activity = list(
        db.scalars(
            select(AuditLog)
            .outerjoin(User, AuditLog.actor_user_id == User.id)
            .where(or_(AuditLog.actor_user_id.is_(None), User.company_id == user.company_id))
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        ).all()
    )

    return CommandCenterResponse(
        user=CommandCenterUserSummary(id=user.id, full_name=user.full_name, email=user.email, is_active=user.is_active, roles=[role.name for role in user.roles if role.is_active]),
        priorities=[_task_item(task) for task in priorities],
        follow_ups=follow_ups,
        approvals=approvals,
        deadlines=[_task_item(task) for task in deadlines],
        founder_actions=[_action_item(action) for action in founder_actions],
        business_health={
            "active_clients": active_client_count,
            "open_opportunities": open_opportunity_count,
            "pipeline_value": float(pipeline_value),
            "open_tasks": len(tasks),
            "overdue_tasks": overdue_count,
            "blocked_tasks": blocked_count,
            "active_users": active_user_count,
        },
        alerts=[_task_item(task) for task in alerts],
        quick_actions=["Create founder action", "Create prospect", "Create opportunity", "Create task", "Open approvals", "Review pipeline"],
        counts={
            "users": user_count,
            "active_users": active_user_count,
            "roles": role_count,
            "permissions": permission_count,
            "inactive_users": inactive_user_count,
            "today_priorities": len(priorities),
            "follow_ups": len(follow_ups),
            "approvals": len(approvals),
            "deadlines": len(deadlines),
            "alerts": len(alerts),
            "founder_actions": len(founder_actions),
        },
        recent_activity=[CommandCenterAuditItem.model_validate(item) for item in recent_activity],
    )


@router.get("/actions", response_model=list[FounderActionResponse])
def list_founder_actions(
    current_user: User = Depends(require_permission("command_center.actions.view")),
    db: Session = Depends(get_db),
) -> list[FounderAction]:
    return list(
        db.scalars(
            select(FounderAction)
            .where(FounderAction.company_id == current_user.company_id)
            .order_by(FounderAction.due_date.asc().nullslast(), FounderAction.created_at.desc())
        ).all()
    )


@router.post("/actions", response_model=FounderActionResponse, status_code=status.HTTP_201_CREATED)
def create_founder_action(
    payload: FounderActionCreate,
    current_user: User = Depends(require_permission("command_center.actions.create")),
    db: Session = Depends(get_db),
) -> FounderAction:
    if payload.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid founder action priority.")
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    action = FounderAction(company_id=current_user.company_id, **payload.model_dump())
    db.add(action)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="founder_action.create", entity_type="FounderAction", entity_id=str(action.id)))
    db.commit()
    db.refresh(action)
    return action


@router.patch("/actions/{action_id}", response_model=FounderActionResponse)
def update_founder_action(
    action_id: UUID,
    payload: FounderActionUpdate,
    current_user: User = Depends(require_permission("command_center.actions.edit")),
    db: Session = Depends(get_db),
) -> FounderAction:
    action = db.get(FounderAction, action_id)
    if action is None or action.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Founder action not found.")
    values = payload.model_dump(exclude_unset=True)
    if "priority" in values and values["priority"] not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid founder action priority.")
    if "status" in values and values["status"] not in VALID_ACTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid founder action status.")
    if "owner_user_id" in values and values["owner_user_id"] is not None:
        _validate_owner(db, current_user.company_id, values["owner_user_id"])
    if values.get("status") == "done" and "resolution_date" not in values:
        values["resolution_date"] = datetime.now(timezone.utc)
    for key, value in values.items():
        setattr(action, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="founder_action.update", entity_type="FounderAction", entity_id=str(action.id)))
    db.commit()
    db.refresh(action)
    return action
