from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.shared.models import AuditLog, Permission, Role, User
from app.roles.schemas import PermissionCreate, RoleCreate

router = APIRouter(tags=["roles"])


@router.get("/roles")
def list_roles(
    _: User = Depends(require_permission("roles.view")),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [
        {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
            "permission_ids": [permission.id for permission in role.permissions],
        }
        for role in roles
    ]


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_permission("roles.create")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.scalar(select(Role).where(Role.name == payload.name)) is not None:
        raise HTTPException(status_code=409, detail="A role with this name already exists.")

    permissions = list(db.scalars(select(Permission).where(Permission.id.in_(payload.permission_ids))).all())
    if len(permissions) != len(set(payload.permission_ids)):
        raise HTTPException(status_code=400, detail="One or more permissions do not exist.")

    role = Role(
        name=payload.name,
        description=payload.description,
        permissions=permissions,
    )
    db.add(role)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="role.create",
            entity_type="Role",
            entity_id=str(role.id),
            details=f"Created role {role.name}",
        )
    )
    db.commit()
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "permission_ids": [permission.id for permission in permissions],
    }


@router.get("/permissions")
def list_permissions(
    _: User = Depends(require_permission("permissions.view")),
    db: Session = Depends(get_db),
) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
def create_permission(
    payload: PermissionCreate,
    current_user: User = Depends(require_permission("permissions.create")),
    db: Session = Depends(get_db),
) -> Permission:
    if db.scalar(select(Permission).where(Permission.code == payload.code)) is not None:
        raise HTTPException(status_code=409, detail="A permission with this code already exists.")

    permission = Permission(code=payload.code, description=payload.description)
    db.add(permission)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="permission.create",
            entity_type="Permission",
            entity_id=str(permission.id),
            details=f"Created permission {permission.code}",
        )
    )
    db.commit()
    db.refresh(permission)
    return permission


@router.put("/roles/{role_id}/permissions")
def replace_role_permissions(
    role_id: UUID,
    permission_ids: list[UUID],
    current_user: User = Depends(require_permission("roles.permissions.manage")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")

    permissions = list(db.scalars(select(Permission).where(Permission.id.in_(permission_ids))).all())
    if len(permissions) != len(set(permission_ids)):
        raise HTTPException(status_code=400, detail="One or more permissions do not exist.")

    role.permissions = permissions
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="role.permissions.replace",
            entity_type="Role",
            entity_id=str(role.id),
            details=f"Assigned {len(permissions)} permissions",
        )
    )
    db.commit()
    return {"role_id": role.id, "permission_ids": [permission.id for permission in permissions]}
