from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.company.models import CompanyPolicy, CompanyProfile, Department, Goal, OperatingRule
from app.company.schemas import (
    CompanyCoreResponse, CompanyProfileResponse, CompanyProfileUpdate,
    DepartmentCreate, DepartmentResponse, GoalCreate, GoalResponse, GoalUpdate,
    PolicyCreate, PolicyResponse, RuleCreate, RuleResponse, RuleUpdate,
)
from app.core.database import get_db
from app.shared.models import AuditLog, Company, User

router = APIRouter(prefix="/company", tags=["company"])


def _owner(db: Session, company_id: UUID, owner_id: UUID | None) -> None:
    if owner_id is None:
        return
    user = db.get(User, owner_id)
    if user is None or user.company_id != company_id or not user.is_active:
        raise HTTPException(status_code=400, detail="Owner must be an active user in the company.")


def _profile(db: Session, company_id: UUID) -> CompanyProfile:
    profile = db.scalar(select(CompanyProfile).where(CompanyProfile.company_id == company_id))
    if profile is None:
        profile = CompanyProfile(company_id=company_id)
        db.add(profile)
        db.flush()
    return profile


@router.get("", response_model=CompanyCoreResponse)
def get_company_core(current_user: User = Depends(require_permission("company.view")), db: Session = Depends(get_db)) -> CompanyCoreResponse:
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    return CompanyCoreResponse(
        company={"id": company.id, "name": company.name, "code": company.code, "is_active": company.is_active},
        profile=_profile(db, company.id),
        departments=list(db.scalars(select(Department).where(Department.company_id == company.id).order_by(Department.name)).all()),
        goals=list(db.scalars(select(Goal).where(Goal.company_id == company.id).order_by(Goal.priority, Goal.title)).all()),
        policies=list(db.scalars(select(CompanyPolicy).where(CompanyPolicy.company_id == company.id).order_by(CompanyPolicy.title)).all()),
        operating_rules=list(db.scalars(select(OperatingRule).where(OperatingRule.company_id == company.id).order_by(OperatingRule.priority, OperatingRule.name)).all()),
    )


@router.patch("/profile", response_model=CompanyProfileResponse)
def update_company_profile(payload: CompanyProfileUpdate, current_user: User = Depends(require_permission("company.edit")), db: Session = Depends(get_db)) -> CompanyProfile:
    profile = _profile(db, current_user.company_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="company.profile.update", entity_type="CompanyProfile", entity_id=str(profile.id), details=",".join(payload.model_dump(exclude_unset=True))))
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, current_user: User = Depends(require_permission("company.departments.manage")), db: Session = Depends(get_db)) -> Department:
    _owner(db, current_user.company_id, payload.owner_user_id)
    if db.scalar(select(Department).where(Department.company_id == current_user.company_id, Department.code == payload.code)):
        raise HTTPException(status_code=409, detail="Department code already exists.")
    item = Department(company_id=current_user.company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="company.department.create", entity_type="Department", entity_id=str(item.id), details=item.code))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: UUID, payload: DepartmentCreate, current_user: User = Depends(require_permission("company.departments.manage")), db: Session = Depends(get_db)) -> Department:
    item = db.get(Department, department_id)
    if item is None or item.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Department not found.")
    _owner(db, current_user.company_id, payload.owner_user_id)
    changes = payload.model_dump()
    duplicate = db.scalar(select(Department).where(Department.company_id == current_user.company_id, Department.code == changes["code"], Department.id != item.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Department code already exists.")
    for key, value in changes.items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="company.department.update", entity_type="Department", entity_id=str(item.id), details=item.code))
    db.commit()
    db.refresh(item)
    return item


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, current_user: User = Depends(require_permission("company.goals.manage")), db: Session = Depends(get_db)) -> Goal:
    _owner(db, current_user.company_id, payload.owner_user_id)
    item = Goal(company_id=current_user.company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="company.goal.create", entity_type="Goal", entity_id=str(item.id), details=item.title))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: UUID, payload: GoalUpdate, current_user: User = Depends(require_permission("company.goals.manage")), db: Session = Depends(get_db)) -> Goal:
    item = db.get(Goal, goal_id)
    if item is None or item.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Goal not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "owner_user_id" in changes:
        _owner(db, current_user.company_id, changes["owner_user_id"])
    for key, value in changes.items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="company.goal.update", entity_type="Goal", entity_id=str(item.id), details=",".join(changes)))
    db.commit()
    db.refresh(item)
    return item


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyCreate, current_user: User = Depends(require_permission("company.policies.manage")), db: Session = Depends(get_db)) -> CompanyPolicy:
    item = CompanyPolicy(company_id=current_user.company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="company.policy.create", entity_type="CompanyPolicy", entity_id=str(item.id), details=item.title))
    db.commit()
    db.refresh(item)
    return item


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate, current_user: User = Depends(require_permission("company.rules.manage")), db: Session = Depends(get_db)) -> OperatingRule:
    item = OperatingRule(company_id=current_user.company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="company.rule.create", entity_type="OperatingRule", entity_id=str(item.id), details=item.name))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: UUID, payload: RuleUpdate, current_user: User = Depends(require_permission("company.rules.manage")), db: Session = Depends(get_db)) -> OperatingRule:
    item = db.get(OperatingRule, rule_id)
    if item is None or item.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Operating rule not found.")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="company.rule.update", entity_type="OperatingRule", entity_id=str(item.id), details=",".join(changes)))
    db.commit()
    db.refresh(item)
    return item
