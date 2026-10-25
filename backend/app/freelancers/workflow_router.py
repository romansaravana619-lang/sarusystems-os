from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.projects.models import Project
from app.shared.models import AuditLog, User
from app.freelancers.models import Freelancer, FreelancerAgreement, FreelancerApplication, FreelancerAssignment
from app.freelancers.schemas import (
    AGREEMENT_STATUSES,
    APPLICATION_STATUSES,
    ASSIGNMENT_STATUSES,
    AgreementResponse,
    ApplicationResponse,
    AssignmentResponse,
)

router = APIRouter(prefix="/freelancers", tags=["freelancers"])

APPLICATION_TRANSITIONS = {
    "received": {"screening", "withdrawn"},
    "screening": {"shortlisted", "rejected", "withdrawn"},
    "shortlisted": {"interview", "rejected", "withdrawn"},
    "interview": {"selected", "rejected", "withdrawn"},
    "selected": set(),
    "rejected": {"screening"},
    "withdrawn": set(),
}

AGREEMENT_TRANSITIONS = {
    "draft": {"pending_signature", "terminated"},
    "pending_signature": {"active", "terminated"},
    "active": {"expired", "terminated"},
    "expired": set(),
    "terminated": set(),
}

class ApplicationTransition(BaseModel):
    status: str

class AgreementUpdate(BaseModel):
    status: str | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    document_url: str | None = None
    notes: str | None = None


def _freelancer(db: Session, company_id: UUID, freelancer_id: UUID) -> Freelancer:
    freelancer = db.get(Freelancer, freelancer_id)
    if freelancer is None or freelancer.company_id != company_id:
        raise HTTPException(status_code=404, detail="Freelancer not found.")
    return freelancer


def _audit(db: Session, actor: User, action: str, entity: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def _active_allocation(db: Session, freelancer_id: UUID, exclude_assignment_id: UUID | None = None) -> float:
    query = select(func.coalesce(func.sum(FreelancerAssignment.allocation_percent), 0)).where(
        FreelancerAssignment.freelancer_id == freelancer_id,
        FreelancerAssignment.status.in_(["proposed", "approved", "active"]),
    )
    if exclude_assignment_id:
        query = query.where(FreelancerAssignment.id != exclude_assignment_id)
    return float(db.scalar(query) or 0)


def _validate_assignment_eligibility(
    db: Session,
    freelancer: Freelancer,
    project: Project,
    allocation_percent: float,
    status_value: str,
    exclude_assignment_id: UUID | None = None,
) -> None:
    if freelancer.status != "active":
        raise HTTPException(status_code=409, detail="Only active freelancers can be assigned to projects.")
    if status_value in {"approved", "active"}:
        agreement = db.scalar(
            select(FreelancerAgreement)
            .where(FreelancerAgreement.freelancer_id == freelancer.id, FreelancerAgreement.status == "active")
            .order_by(FreelancerAgreement.created_at.desc())
        )
        if agreement is None or (agreement.expires_at and agreement.expires_at < datetime.now(timezone.utc)):
            raise HTTPException(status_code=409, detail="An active, non-expired freelancer agreement is required before assignment.")
    if status_value in {"approved", "active"} and freelancer.availability_status in {"busy", "unavailable"}:
        raise HTTPException(status_code=409, detail="Freelancer availability does not allow a new active assignment.")
    if allocation_percent <= 0 or allocation_percent > 100:
        raise HTTPException(status_code=422, detail="Allocation must be between 0 and 100 percent.")
    if _active_allocation(db, freelancer.id, exclude_assignment_id) + allocation_percent > 100:
        raise HTTPException(status_code=409, detail="Freelancer allocation would exceed 100 percent capacity.")
    if project.company_id != freelancer.company_id:
        raise HTTPException(status_code=403, detail="Project and freelancer must belong to the same company.")


@router.patch("/applications/{application_id}/status", response_model=ApplicationResponse)
def transition_application(
    application_id: UUID,
    payload: ApplicationTransition,
    current_user: User = Depends(require_permission("freelancers.applications.edit")),
    db: Session = Depends(get_db),
) -> FreelancerApplication:
    application = db.scalar(
        select(FreelancerApplication).where(
            FreelancerApplication.id == application_id,
            FreelancerApplication.company_id == current_user.company_id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid application status.")
    if payload.status != application.status and payload.status not in APPLICATION_TRANSITIONS.get(application.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid application lifecycle transition: {application.status} -> {payload.status}.")
    application.status = payload.status
    _audit(db, current_user, "freelancer.application.status", "FreelancerApplication", application.id, f"{payload.status}")
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{freelancer_id}/agreements/{agreement_id}", response_model=AgreementResponse)
def update_agreement(
    freelancer_id: UUID,
    agreement_id: UUID,
    payload: AgreementUpdate,
    current_user: User = Depends(require_permission("freelancers.agreements.manage")),
    db: Session = Depends(get_db),
) -> FreelancerAgreement:
    _freelancer(db, current_user.company_id, freelancer_id)
    agreement = db.scalar(select(FreelancerAgreement).where(FreelancerAgreement.id == agreement_id, FreelancerAgreement.freelancer_id == freelancer_id))
    if agreement is None:
        raise HTTPException(status_code=404, detail="Agreement not found.")
    values = payload.model_dump(exclude_unset=True)
    target = values.get("status", agreement.status)
    if target not in AGREEMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid agreement status.")
    if target != agreement.status and target not in AGREEMENT_TRANSITIONS.get(agreement.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid agreement lifecycle transition: {agreement.status} -> {target}.")
    if target == "active":
        effective_at = values.get("effective_at", agreement.effective_at)
        expires_at = values.get("expires_at", agreement.expires_at)
        if effective_at is None:
            raise HTTPException(status_code=409, detail="An effective date is required before activating an agreement.")
        if expires_at and expires_at <= effective_at:
            raise HTTPException(status_code=422, detail="Agreement expiry must be after its effective date.")
    for key, value in values.items():
        setattr(agreement, key, value)
    _audit(db, current_user, "freelancer.agreement.update", "FreelancerAgreement", agreement.id, f"{target}")
    db.commit()
    db.refresh(agreement)
    return agreement


@router.post("/{freelancer_id}/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_eligible_assignment(
    freelancer_id: UUID,
    payload,
    current_user: User = Depends(require_permission("freelancers.assign")),
    db: Session = Depends(get_db),
) -> FreelancerAssignment:
    from app.freelancers.schemas import AssignmentCreate

    data = AssignmentCreate.model_validate(payload)
    freelancer = _freelancer(db, current_user.company_id, freelancer_id)
    project = db.get(Project, data.project_id)
    if project is None or project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Project not found.")
    if data.status not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid assignment status.")
    _validate_assignment_eligibility(db, freelancer, project, data.allocation_percent, data.status)
    assignment = FreelancerAssignment(freelancer_id=freelancer.id, **data.model_dump())
    db.add(assignment)
    db.flush()
    _audit(db, current_user, "freelancer.assignment.create", "FreelancerAssignment", assignment.id, "eligibility checks passed")
    db.commit()
    db.refresh(assignment)
    return assignment


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_eligible_assignment(
    assignment_id: UUID,
    payload,
    current_user: User = Depends(require_permission("freelancers.assign")),
    db: Session = Depends(get_db),
) -> FreelancerAssignment:
    from app.freelancers.schemas import AssignmentUpdate

    assignment = db.get(FreelancerAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    freelancer = _freelancer(db, current_user.company_id, assignment.freelancer_id)
    values = AssignmentUpdate.model_validate(payload).model_dump(exclude_unset=True)
    target = values.get("status", assignment.status)
    if target not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid assignment status.")
    project = db.get(Project, assignment.project_id)
    if project is None or project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Project not found.")
    allocation = values.get("allocation_percent", float(assignment.allocation_percent))
    _validate_assignment_eligibility(db, freelancer, project, allocation, target, assignment.id)
    for key, value in values.items():
        setattr(assignment, key, value)
    _audit(db, current_user, "freelancer.assignment.update", "FreelancerAssignment", assignment.id, "eligibility checks passed")
    db.commit()
    db.refresh(assignment)
    return assignment
