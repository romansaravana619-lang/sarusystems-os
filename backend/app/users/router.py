from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.shared.models import AuditLog, Company, Role, User
from app.users.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)).all())


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("users.create")),
    db: Session = Depends(get_db),
) -> User:
    company = db.get(Company, payload.company_id)
    if company is None or not company.is_active:
        raise HTTPException(status_code=400, detail="Active company is required.")

    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    roles = list(db.scalars(select(Role).where(Role.id.in_(payload.role_ids))).all())
    if len(roles) != len(set(payload.role_ids)):
        raise HTTPException(status_code=400, detail="One or more roles do not exist.")
    if any(not role.is_active for role in roles):
        raise HTTPException(status_code=400, detail="Inactive roles cannot be assigned.")

    user = User(
        company_id=company.id,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        roles=roles,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="user.create",
            entity_type="User",
            entity_id=str(user.id),
            details=f"Created user {user.email}",
        )
    )
    db.commit()
    db.refresh(user)
    return user
