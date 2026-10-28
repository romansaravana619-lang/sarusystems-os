from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, MeResponse, TokenResponse
from app.auth.tokens import create_access_token
from app.core.database import get_db
from app.core.security import verify_password
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="auth.login",
            entity_type="User",
            entity_id=str(user.id),
            details="Successful login",
        )
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="auth.logout",
            entity_type="User",
            entity_id=str(current_user.id),
            details="Logout requested",
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/refresh", response_model=TokenResponse)
def refresh(current_user: User = Depends(get_current_user)) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(current_user.id))


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    roles = sorted({role.name for role in current_user.roles})
    permissions = sorted(
        {
            permission.code
            for role in current_user.roles
            for permission in role.permissions
        }
    )
    return MeResponse(
        id=current_user.id,
        company_id=current_user.company_id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=roles,
        permissions=permissions,
    )
