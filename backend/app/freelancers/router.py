from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.projects.models import Project
from app.shared.models import AuditLog, User
from app.freelancers.models import Freelancer, FreelancerAgreement, FreelancerApplication, FreelancerAvailability, FreelancerEvaluation, FreelancerPerformance, FreelancerSkill, FreelancerAssignment
from app.freelancers.schemas import (
    AGREEMENT_STATUSES, APPLICATION_STATUSES, ASSIGNMENT_STATUSES, AVAILABILITY_STATUSES, FREELANCER_STATUSES,
    AgreementCreate, AgreementResponse, ApplicationCreate, ApplicationResponse, ApplicationUpdate,
    AssignmentCreate, AssignmentResponse, AssignmentUpdate, AvailabilityCreate, AvailabilityResponse,
    EvaluationCreate, EvaluationResponse, FreelancerCreate, FreelancerResponse, FreelancerUpdate,
    FreelancerWorkspaceResponse, PerformanceCreate, PerformanceResponse, SkillCreate, SkillResponse,
)

router = APIRouter(prefix="/freelancers", tags=["freelancers"])

TRANSITIONS = {
    "prospect": {"screening", "rejected", "blacklisted"},
    "screening": {"approved", "rejected", "blacklisted"},
    "approved": {"onboarding", "inactive", "blacklisted"},
    "onboarding": {"active", "rejected", "inactive"},
    "active": {"inactive", "blacklisted"},
    "inactive": {"active", "blacklisted"},
    "rejected": {"prospect"},
    "blacklisted": set(),
}


def _freelancer(db: Session, company_id: UUID, freelancer_id: UUID) -> Freelancer:
    freelancer = db.get(Freelancer, freelancer_id)
    if freelancer is None or freelancer.company_id != company_id:
        raise HTTPException(status_code=404, detail="Freelancer not found.")
    return freelancer


def _audit(db: Session, actor: User, action: str, entity: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def _validate_status(current: str, target: str) -> None:
    if target not in FREELANCER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid freelancer status.")
    if target != current and target not in TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid freelancer lifecycle transition: {current} -> {target}.")


def _validate_agreement_active(db: Session, freelancer_id: UUID) -> None:
    agreement = db.scalar(select(FreelancerAgreement).where(FreelancerAgreement.freelancer_id == freelancer_id, FreelancerAgreement.status == "active").order_by(FreelancerAgreement.created_at.desc()))
    if agreement is None:
        raise HTTPException(status_code=409, detail="An active freelancer agreement is required before assignment.")
    now = datetime.now(timezone.utc)
    if agreement.expires_at and agreement.expires_at < now:
        raise HTTPException(status_code=409, detail="The freelancer agreement has expired.")


@router.get("/workspace", response_model=FreelancerWorkspaceResponse)
def workspace(current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> FreelancerWorkspaceResponse:
    freelancers = list(db.scalars(select(Freelancer).where(Freelancer.company_id == current_user.company_id).order_by(Freelancer.created_at.desc())).all())
    applications = db.scalar(select(func.count(FreelancerApplication.id)).where(FreelancerApplication.company_id == current_user.company_id)) or 0
    shortlisted = db.scalar(select(func.count(FreelancerApplication.id)).where(FreelancerApplication.company_id == current_user.company_id, FreelancerApplication.status == "shortlisted")) or 0
    active_assignments = db.scalar(select(func.count(FreelancerAssignment.id)).join(Freelancer, Freelancer.id == FreelancerAssignment.freelancer_id).where(Freelancer.company_id == current_user.company_id, FreelancerAssignment.status == "active")) or 0
    return FreelancerWorkspaceResponse(
        total=len(freelancers), active=sum(f.status == "active" for f in freelancers), available=sum(f.availability_status == "available" for f in freelancers),
        onboarding=sum(f.status == "onboarding" for f in freelancers), screening=sum(f.status == "screening" for f in freelancers), inactive=sum(f.status == "inactive" for f in freelancers),
        applications=applications, shortlisted_applications=shortlisted, active_assignments=active_assignments, freelancers=freelancers,
    )


@router.get("", response_model=list[FreelancerResponse])
def list_freelancers(current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> list[Freelancer]:
    return list(db.scalars(select(Freelancer).where(Freelancer.company_id == current_user.company_id).order_by(Freelancer.created_at.desc())).all())


@router.post("", response_model=FreelancerResponse, status_code=status.HTTP_201_CREATED)
def create_freelancer(payload: FreelancerCreate, current_user: User = Depends(require_permission("freelancers.create")), db: Session = Depends(get_db)) -> Freelancer:
    existing = db.scalar(select(Freelancer).where(Freelancer.company_id == current_user.company_id, Freelancer.email == payload.email))
    if existing: raise HTTPException(status_code=409, detail="A freelancer with this email already exists.")
    freelancer = Freelancer(company_id=current_user.company_id, freelancer_code="PENDING", **payload.model_dump())
    db.add(freelancer); db.flush(); freelancer.freelancer_code = f"FL-{freelancer.id.hex[:8].upper()}"
    _audit(db, current_user, "freelancer.create", "Freelancer", freelancer.id)
    db.commit(); db.refresh(freelancer); return freelancer


@router.get("/{freelancer_id}", response_model=FreelancerResponse)
def get_freelancer(freelancer_id: UUID, current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> Freelancer:
    return _freelancer(db, current_user.company_id, freelancer_id)


@router.patch("/{freelancer_id}", response_model=FreelancerResponse)
def update_freelancer(freelancer_id: UUID, payload: FreelancerUpdate, current_user: User = Depends(require_permission("freelancers.edit")), db: Session = Depends(get_db)) -> Freelancer:
    freelancer = _freelancer(db, current_user.company_id, freelancer_id)
    values = payload.model_dump(exclude_unset=True)
    target = values.get("status", freelancer.status)
    _validate_status(freelancer.status, target)
    if "email" in values and values["email"] != freelancer.email and db.scalar(select(Freelancer.id).where(Freelancer.company_id == current_user.company_id, Freelancer.email == values["email"], Freelancer.id != freelancer.id)):
        raise HTTPException(status_code=409, detail="A freelancer with this email already exists.")
    for key, value in values.items(): setattr(freelancer, key, value)
    _audit(db, current_user, "freelancer.update", "Freelancer", freelancer.id)
    db.commit(); db.refresh(freelancer); return freelancer


@router.get("/{freelancer_id}/skills", response_model=list[SkillResponse])
def list_skills(freelancer_id: UUID, current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> list[FreelancerSkill]:
    _freelancer(db, current_user.company_id, freelancer_id)
    return list(db.scalars(select(FreelancerSkill).where(FreelancerSkill.freelancer_id == freelancer_id)).all())

@router.post("/{freelancer_id}/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def add_skill(freelancer_id: UUID, payload: SkillCreate, current_user: User = Depends(require_permission("freelancers.edit")), db: Session = Depends(get_db)) -> FreelancerSkill:
    _freelancer(db, current_user.company_id, freelancer_id)
    skill = FreelancerSkill(freelancer_id=freelancer_id, **payload.model_dump()); db.add(skill); db.flush(); _audit(db, current_user, "freelancer.skill.add", "FreelancerSkill", skill.id); db.commit(); db.refresh(skill); return skill


@router.get("/applications/list", response_model=list[ApplicationResponse])
def list_applications(current_user: User = Depends(require_permission("freelancers.applications.view")), db: Session = Depends(get_db)) -> list[FreelancerApplication]:
    return list(db.scalars(select(FreelancerApplication).where(FreelancerApplication.company_id == current_user.company_id).order_by(FreelancerApplication.created_at.desc())).all())

@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, current_user: User = Depends(require_permission("freelancers.applications.create")), db: Session = Depends(get_db)) -> FreelancerApplication:
    if payload.status not in APPLICATION_STATUSES: raise HTTPException(status_code=400, detail="Invalid application status.")
    application = FreelancerApplication(company_id=current_user.company_id, **payload.model_dump()); db.add(application); db.flush(); _audit(db, current_user, "freelancer.application.create", "FreelancerApplication", application.id); db.commit(); db.refresh(application); return application

@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: UUID, payload: ApplicationUpdate, current_user: User = Depends(require_permission("freelancers.applications.edit")), db: Session = Depends(get_db)) -> FreelancerApplication:
    application = db.scalar(select(FreelancerApplication).where(FreelancerApplication.id == application_id, FreelancerApplication.company_id == current_user.company_id))
    if application is None: raise HTTPException(status_code=404, detail="Application not found.")
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in APPLICATION_STATUSES: raise HTTPException(status_code=400, detail="Invalid application status.")
    if "freelancer_id" in values and values["freelancer_id"] is not None: _freelancer(db, current_user.company_id, values["freelancer_id"])
    for key, value in values.items(): setattr(application, key, value)
    _audit(db, current_user, "freelancer.application.update", "FreelancerApplication", application.id); db.commit(); db.refresh(application); return application

@router.post("/applications/{application_id}/convert", response_model=FreelancerResponse, status_code=status.HTTP_201_CREATED)
def convert_application(application_id: UUID, current_user: User = Depends(require_permission("freelancers.applications.convert")), db: Session = Depends(get_db)) -> Freelancer:
    application = db.scalar(select(FreelancerApplication).where(FreelancerApplication.id == application_id, FreelancerApplication.company_id == current_user.company_id))
    if application is None: raise HTTPException(status_code=404, detail="Application not found.")
    if application.status != "selected": raise HTTPException(status_code=409, detail="Only selected applications can be converted to a freelancer.")
    if application.freelancer_id: return _freelancer(db, current_user.company_id, application.freelancer_id)
    existing = db.scalar(select(Freelancer).where(Freelancer.company_id == current_user.company_id, Freelancer.email == application.email))
    if existing: application.freelancer_id = existing.id; db.commit(); return existing
    freelancer = Freelancer(company_id=current_user.company_id, freelancer_code="PENDING", full_name=application.name, email=application.email, phone=application.phone, primary_role=application.role_applied, portfolio_url=application.portfolio_url, resume_url=application.resume_url, source=application.source, notes=application.notes, status="approved")
    db.add(freelancer); db.flush(); freelancer.freelancer_code=f"FL-{freelancer.id.hex[:8].upper()}"; application.freelancer_id=freelancer.id
    _audit(db, current_user, "freelancer.application.convert", "Freelancer", freelancer.id, f"Converted application {application.id}"); db.commit(); db.refresh(freelancer); return freelancer

@router.post("/{freelancer_id}/evaluations/{application_id}", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def evaluate_application(freelancer_id: UUID, application_id: UUID, payload: EvaluationCreate, current_user: User = Depends(require_permission("freelancers.evaluations.create")), db: Session = Depends(get_db)) -> FreelancerEvaluation:
    _freelancer(db, current_user.company_id, freelancer_id)
    application = db.scalar(select(FreelancerApplication).where(FreelancerApplication.id == application_id, FreelancerApplication.company_id == current_user.company_id))
    if application is None: raise HTTPException(status_code=404, detail="Application not found.")
    evaluation = FreelancerEvaluation(application_id=application.id, evaluator_user_id=current_user.id, **payload.model_dump()); db.add(evaluation); db.flush(); _audit(db, current_user, "freelancer.evaluation.create", "FreelancerEvaluation", evaluation.id); db.commit(); db.refresh(evaluation); return evaluation

@router.post("/{freelancer_id}/agreements", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
def create_agreement(freelancer_id: UUID, payload: AgreementCreate, current_user: User = Depends(require_permission("freelancers.agreements.manage")), db: Session = Depends(get_db)) -> FreelancerAgreement:
    _freelancer(db, current_user.company_id, freelancer_id)
    if payload.status not in AGREEMENT_STATUSES: raise HTTPException(status_code=400, detail="Invalid agreement status.")
    agreement = FreelancerAgreement(freelancer_id=freelancer_id, **payload.model_dump()); db.add(agreement); db.flush(); _audit(db, current_user, "freelancer.agreement.create", "FreelancerAgreement", agreement.id); db.commit(); db.refresh(agreement); return agreement

@router.get("/{freelancer_id}/agreements", response_model=list[AgreementResponse])
def list_agreements(freelancer_id: UUID, current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> list[FreelancerAgreement]:
    _freelancer(db, current_user.company_id, freelancer_id); return list(db.scalars(select(FreelancerAgreement).where(FreelancerAgreement.freelancer_id == freelancer_id).order_by(FreelancerAgreement.created_at.desc())).all())

@router.post("/{freelancer_id}/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
def set_availability(freelancer_id: UUID, payload: AvailabilityCreate, current_user: User = Depends(require_permission("freelancers.availability.manage")), db: Session = Depends(get_db)) -> FreelancerAvailability:
    freelancer = _freelancer(db, current_user.company_id, freelancer_id)
    if payload.status not in AVAILABILITY_STATUSES: raise HTTPException(status_code=400, detail="Invalid availability status.")
    freelancer.availability_status=payload.status
    availability=FreelancerAvailability(freelancer_id=freelancer_id, **payload.model_dump()); db.add(availability); db.flush(); _audit(db, current_user, "freelancer.availability.update", "FreelancerAvailability", availability.id); db.commit(); db.refresh(availability); return availability

@router.post("/{freelancer_id}/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(freelancer_id: UUID, payload: AssignmentCreate, current_user: User = Depends(require_permission("freelancers.assign")), db: Session = Depends(get_db)) -> FreelancerAssignment:
    freelancer=_freelancer(db, current_user.company_id, freelancer_id)
    project=db.get(Project, payload.project_id)
    if project is None or project.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Project not found.")
    if freelancer.status != "active": raise HTTPException(status_code=409, detail="Only active freelancers can be assigned to projects.")
    if payload.status not in ASSIGNMENT_STATUSES: raise HTTPException(status_code=400, detail="Invalid assignment status.")
    if payload.status in {"approved", "active"}: _validate_agreement_active(db, freelancer.id)
    assignment=FreelancerAssignment(freelancer_id=freelancer.id, **payload.model_dump()); db.add(assignment); db.flush(); _audit(db, current_user, "freelancer.assignment.create", "FreelancerAssignment", assignment.id); db.commit(); db.refresh(assignment); return assignment

@router.get("/{freelancer_id}/assignments", response_model=list[AssignmentResponse])
def list_assignments(freelancer_id: UUID, current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> list[FreelancerAssignment]:
    _freelancer(db, current_user.company_id, freelancer_id); return list(db.scalars(select(FreelancerAssignment).where(FreelancerAssignment.freelancer_id == freelancer_id).order_by(FreelancerAssignment.created_at.desc())).all())

@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(assignment_id: UUID, payload: AssignmentUpdate, current_user: User = Depends(require_permission("freelancers.assign")), db: Session = Depends(get_db)) -> FreelancerAssignment:
    assignment=db.get(FreelancerAssignment, assignment_id)
    if assignment is None: raise HTTPException(status_code=404, detail="Assignment not found.")
    _freelancer(db, current_user.company_id, assignment.freelancer_id)
    values=payload.model_dump(exclude_unset=True)
    target=values.get("status", assignment.status)
    if target not in ASSIGNMENT_STATUSES: raise HTTPException(status_code=400, detail="Invalid assignment status.")
    if target in {"approved", "active"}: _validate_agreement_active(db, assignment.freelancer_id)
    for key,value in values.items(): setattr(assignment,key,value)
    _audit(db,current_user,"freelancer.assignment.update","FreelancerAssignment",assignment.id); db.commit(); db.refresh(assignment); return assignment

@router.post("/{freelancer_id}/performance", response_model=PerformanceResponse, status_code=status.HTTP_201_CREATED)
def add_performance(freelancer_id: UUID, payload: PerformanceCreate, current_user: User = Depends(require_permission("freelancers.performance.manage")), db: Session = Depends(get_db)) -> FreelancerPerformance:
    _freelancer(db, current_user.company_id, freelancer_id)
    if payload.project_id:
        project=db.get(Project,payload.project_id)
        if project is None or project.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Project not found.")
    record=FreelancerPerformance(freelancer_id=freelancer_id, **payload.model_dump()); db.add(record); db.flush(); _audit(db,current_user,"freelancer.performance.create","FreelancerPerformance",record.id); db.commit(); db.refresh(record); return record

@router.get("/{freelancer_id}/performance", response_model=list[PerformanceResponse])
def list_performance(freelancer_id: UUID, current_user: User = Depends(require_permission("freelancers.view")), db: Session = Depends(get_db)) -> list[FreelancerPerformance]:
    _freelancer(db, current_user.company_id, freelancer_id); return list(db.scalars(select(FreelancerPerformance).where(FreelancerPerformance.freelancer_id == freelancer_id).order_by(FreelancerPerformance.created_at.desc())).all())
