from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_logs(
    _: User = Depends(require_permission("audit.view")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    return list(db.scalars(statement).all())


@router.get("/{entity_type}/{entity_id}")
def entity_audit_history(
    entity_type: str,
    entity_id: str,
    _: User = Depends(require_permission("audit.view")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.desc())
    )
    return list(db.scalars(statement).all())
