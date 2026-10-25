from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import require_permission
from app.command_center.schemas import CommandCenterAuditItem, CommandCenterResponse, CommandCenterUserSummary
from app.core.database import get_db
from app.shared.models import AuditLog, Permission, Role, User

router = APIRouter(prefix="/command-center", tags=["command-center"])


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

    user_count = db.scalar(select(func.count(User.id)).where(User.company_id == user.company_id)) or 0
    active_user_count = db.scalar(
        select(func.count(User.id)).where(User.company_id == user.company_id, User.is_active.is_(True))
    ) or 0
    inactive_user_count = user_count - active_user_count
    role_count = db.scalar(select(func.count(Role.id)).where(Role.is_active.is_(True))) or 0
    permission_count = db.scalar(select(func.count(Permission.id))) or 0
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
        attention={
            "inactive_users": inactive_user_count,
            "recent_audit_events": len(recent_activity),
        },
        counts={
            "users": user_count,
            "active_users": active_user_count,
            "roles": role_count,
            "permissions": permission_count,
        },
        recent_activity=[CommandCenterAuditItem.model_validate(item) for item in recent_activity],
    )
