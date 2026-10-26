from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.core.database import get_db
from app.finance.models import FinancialTransaction, PaymentMilestone
from app.finance.schemas import (
    FinanceDashboard,
    MilestoneCreate,
    MilestoneOut,
    PaymentRecord,
    ProjectProfitability,
    TransactionCreate,
    TransactionOut,
)
from app.freelancers.models import Freelancer
from app.projects.models import Project
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/finance", tags=["Finance & Payments"])


PERMISSION_VIEW_DASHBOARD = "finance.dashboard.view"
PERMISSION_VIEW_TRANSACTIONS = "finance.transactions.view"
PERMISSION_CREATE_TRANSACTIONS = "finance.transactions.create"
PERMISSION_VIEW_MILESTONES = "finance.milestones.view"
PERMISSION_CREATE_MILESTONES = "finance.milestones.create"
PERMISSION_RECORD_PAYMENTS = "finance.payments.record"
PERMISSION_VIEW_PROFITABILITY = "finance.profitability.view"


def _audit(db: Session, actor: User, action: str, entity_type: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=str(entity_id), details=details))


def _client(db: Session, company_id: UUID, client_id: UUID | None) -> Client | None:
    if client_id is None:
        return None
    item = db.scalar(select(Client).where(Client.id == client_id, Client.company_id == company_id))
    if item is None:
        raise HTTPException(400, "Referenced client does not exist in this company.")
    return item


def _project(db: Session, company_id: UUID, project_id: UUID | None) -> Project | None:
    if project_id is None:
        return None
    item = db.scalar(select(Project).where(Project.id == project_id, Project.company_id == company_id))
    if item is None:
        raise HTTPException(400, "Referenced project does not exist in this company.")
    return item


def _freelancer(db: Session, company_id: UUID, freelancer_id: UUID | None) -> Freelancer | None:
    if freelancer_id is None:
        return None
    item = db.scalar(select(Freelancer).where(Freelancer.id == freelancer_id, Freelancer.company_id == company_id))
    if item is None:
        raise HTTPException(400, "Referenced freelancer does not exist in this company.")
    return item


def _validate_relationships(db: Session, company_id: UUID, project_id: UUID | None, client_id: UUID | None, freelancer_id: UUID | None) -> None:
    project = _project(db, company_id, project_id)
    client = _client(db, company_id, client_id)
    _freelancer(db, company_id, freelancer_id)
    if project is not None and client is not None and project.client_id != client.id:
        raise HTTPException(400, "Project and client references do not belong together.")


def _milestone(db: Session, company_id: UUID, milestone_id: UUID) -> PaymentMilestone:
    item = db.scalar(select(PaymentMilestone).where(PaymentMilestone.id == milestone_id, PaymentMilestone.company_id == company_id))
    if item is None:
        raise HTTPException(404, "Payment milestone not found.")
    return item


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    category: str | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    current_user: User = Depends(require_permission(PERMISSION_VIEW_TRANSACTIONS)),
    db: Session = Depends(get_db),
):
    query = select(FinancialTransaction).where(FinancialTransaction.company_id == current_user.company_id)
    if category:
        query = query.where(FinancialTransaction.category == category)
    if transaction_type:
        query = query.where(FinancialTransaction.transaction_type == transaction_type)
    if project_id:
        query = query.where(FinancialTransaction.project_id == project_id)
    if client_id:
        query = query.where(FinancialTransaction.client_id == client_id)
    return list(db.scalars(query.order_by(FinancialTransaction.transaction_date.desc(), FinancialTransaction.created_at.desc())).all())


@router.post("/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(require_permission(PERMISSION_CREATE_TRANSACTIONS)),
    db: Session = Depends(get_db),
):
    _validate_relationships(db, current_user.company_id, payload.project_id, payload.client_id, payload.freelancer_id)
    if payload.transaction_type == "expense" and payload.category == "freelancer" and payload.freelancer_id is None:
        raise HTTPException(422, "Freelancer expenses require a freelancer reference.")
    if payload.transaction_type == "income" and payload.category == "client_payment" and payload.client_id is None:
        raise HTTPException(422, "Client payments require a client reference.")
    values = payload.model_dump()
    item = FinancialTransaction(company_id=current_user.company_id, created_by=current_user.id, **values)
    db.add(item)
    db.flush()
    _audit(db, current_user, "finance.transaction.create", "FinancialTransaction", item.id, f"{item.transaction_type}:{item.category}:{item.amount}")
    db.commit()
    db.refresh(item)
    return item


@router.get("/milestones", response_model=list[MilestoneOut])
def list_milestones(
    status_filter: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    current_user: User = Depends(require_permission(PERMISSION_VIEW_MILESTONES)),
    db: Session = Depends(get_db),
):
    query = select(PaymentMilestone).where(PaymentMilestone.company_id == current_user.company_id)
    if status_filter:
        query = query.where(PaymentMilestone.status == status_filter)
    if project_id:
        query = query.where(PaymentMilestone.project_id == project_id)
    if client_id:
        query = query.where(PaymentMilestone.client_id == client_id)
    return list(db.scalars(query.order_by(PaymentMilestone.due_date.asc().nullslast())).all())


@router.post("/milestones", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_milestone(
    payload: MilestoneCreate,
    current_user: User = Depends(require_permission(PERMISSION_CREATE_MILESTONES)),
    db: Session = Depends(get_db),
):
    if not payload.project_id and not payload.client_id:
        raise HTTPException(422, "A client or project is required.")
    project = _project(db, current_user.company_id, payload.project_id)
    client = _client(db, current_user.company_id, payload.client_id)
    if project is not None and client is not None and project.client_id != client.id:
        raise HTTPException(400, "Project and client references do not belong together.")
    if project is not None and client is None:
        payload.client_id = project.client_id
    item = PaymentMilestone(company_id=current_user.company_id, **payload.model_dump())
    db.add(item)
    db.flush()
    _audit(db, current_user, "finance.milestone.create", "PaymentMilestone", item.id, item.name)
    db.commit()
    db.refresh(item)
    return item


@router.post("/milestones/{milestone_id}/payments", response_model=MilestoneOut)
def record_payment(
    milestone_id: UUID,
    payload: PaymentRecord,
    current_user: User = Depends(require_permission(PERMISSION_RECORD_PAYMENTS)),
    db: Session = Depends(get_db),
):
    item = _milestone(db, current_user.company_id, milestone_id)
    remaining = Decimal(item.amount) - Decimal(item.paid_amount)
    if payload.amount > remaining:
        raise HTTPException(422, "Payment exceeds the outstanding milestone amount.")
    item.paid_amount = Decimal(item.paid_amount) + payload.amount
    item.status = "paid" if item.paid_amount == item.amount else "partially_paid"
    transaction = FinancialTransaction(
        company_id=current_user.company_id,
        created_by=current_user.id,
        transaction_type="income",
        category="client_payment",
        description=f"Payment for milestone: {item.name}",
        amount=payload.amount,
        transaction_date=payload.payment_date,
        reference_type="payment_milestone",
        reference_id=item.id,
        project_id=item.project_id,
        client_id=item.client_id,
        notes=payload.notes,
    )
    db.add(transaction)
    db.flush()
    _audit(db, current_user, "finance.payment.record", "PaymentMilestone", item.id, f"Recorded {payload.amount}")
    db.commit()
    db.refresh(item)
    return item


@router.get("/profitability", response_model=list[ProjectProfitability])
def project_profitability(
    current_user: User = Depends(require_permission(PERMISSION_VIEW_PROFITABILITY)),
    db: Session = Depends(get_db),
):
    projects = list(db.scalars(select(Project).where(Project.company_id == current_user.company_id).order_by(Project.name.asc())).all())
    result: list[ProjectProfitability] = []
    for project in projects:
        revenue = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == current_user.company_id, FinancialTransaction.project_id == project.id, FinancialTransaction.transaction_type == "income")) or Decimal("0")
        expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == current_user.company_id, FinancialTransaction.project_id == project.id, FinancialTransaction.transaction_type == "expense")) or Decimal("0")
        result.append(ProjectProfitability(project_id=project.id, project_name=project.name, revenue=revenue, expenses=expenses, profitability=revenue - expenses))
    return result


@router.get("/dashboard", response_model=FinanceDashboard)
def dashboard(
    current_user: User = Depends(require_permission(PERMISSION_VIEW_DASHBOARD)),
    db: Session = Depends(get_db),
):
    base = FinancialTransaction.company_id == current_user.company_id
    income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "income")) or Decimal("0")
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "expense")) or Decimal("0")
    total_due = db.scalar(select(func.coalesce(func.sum(PaymentMilestone.amount - PaymentMilestone.paid_amount), 0)).where(PaymentMilestone.company_id == current_user.company_id, PaymentMilestone.status != "paid")) or Decimal("0")
    freelancer = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "expense", FinancialTransaction.category == "freelancer")) or Decimal("0")
    software = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "expense", FinancialTransaction.category == "software")) or Decimal("0")
    marketing = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "expense", FinancialTransaction.category == "marketing")) or Decimal("0")
    operating = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(base, FinancialTransaction.transaction_type == "expense", FinancialTransaction.category == "operating")) or Decimal("0")
    reports = project_profitability(current_user, db)
    return FinanceDashboard(revenue=income, expenses=expenses, outstanding=total_due, freelancer_payments=freelancer, project_profitability=income - expenses, software_expenses=software, marketing_expenses=marketing, operating_expenses=operating, project_reports=reports)
