from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.command_center.schemas import (
    CommandCenterApprovalItem,
    CommandCenterAuditItem,
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


@router.get("", response_model=CommandCenterResponse)
def get_command_center(
    current_user: User = Depends(require_permission("command_center.view")),
    db: Session = Depends(get_db),
) -> CommandCenterResponse:
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == current_user.id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Authenticated user was not found")

    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)
    next_week = today_start + timedelta(days=7)

    company_filter = lambda model: model.company_id == user.company_id
    open_task_filter = Task.status.in_(OPEN_TASK_STATUSES)

    tasks = list(
        db.scalars(
            select(Task)
            .where(company_filter(Task), open_task_filter)
            .order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
            .limit(100)
        ).all()
    )
    priorities = sorted(
        [task for task in tasks if task.due_at is not None and task.due_at < tomorrow_start],
        key=lambda task: (PRIORITY_ORDER.get(task.priority.lower(), 9), task.due_at or now),
    )[:10]
    deadlines = [
        task for task in tasks
        if task.due_at is not None and now <= task.due_at < next_week
    ][:10]
    alerts = [
        task for task in tasks
        if task.status == "blocked" or (task.due_at is not None and task.due_at < now)
    ][:10]

    opportunities = list(
        db.scalars(
            select(Opportunity)
            .where(
                Opportunity.company_id == user.company_id,
                Opportunity.stage.in_(OPEN_OPPORTUNITY_STAGES),
            )
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
        CommandCenterApprovalItem(
            id=requirement.id,
            type="requirement",
            description=requirement.description,
            reference_id=requirement.opportunity_id,
        )
        for requirement in pending_requirements
    ]

    user_count = db.scalar(select(func.count(User.id)).where(User.company_id == user.company_id)) or 0
    active_user_count = db.scalar(
        select(func.count(User.id)).where(User.company_id == user.company_id, User.is_active.is_(True))
    ) or 0
    inactive_user_count = user_count - active_user_count
    role_count = db.scalar(select(func.count(Role.id)).where(Role.is_active.is_(True))) or 0
    permission_count = db.scalar(select(func.count(Permission.id))) or 0
    active_client_count = db.scalar(
        select(func.count(Client.id)).where(Client.company_id == user.company_id, Client.status != "closed")
    ) or 0
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
        user=CommandCenterUserSummary(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            roles=[role.name for role in user.roles if role.is_active],
        ),
        priorities=[_task_item(task) for task in priorities],
        follow_ups=follow_ups,
        approvals=approvals,
        deadlines=[_task_item(task) for task in deadlines],
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
        quick_actions=[
            "Create prospect",
            "Create opportunity",
            "Create task",
            "Open approvals",
            "Review pipeline",
        ],
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
        },
        recent_activity=[CommandCenterAuditItem.model_validate(item) for item in recent_activity],
    )
