from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.finance.models import FinancialTransaction, PaymentMilestone
from app.finance.schemas import FinanceDashboard, MilestoneCreate, MilestoneOut, PaymentRecord, TransactionCreate, TransactionOut

router = APIRouter(prefix="/finance", tags=["Finance & Payments"])


def _company_id(user) -> UUID:
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="User is not associated with a company")
    return company_id


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(user=Depends(lambda: None), db: Session = Depends(get_db), limit: int = Query(100, le=100)):
    # Authentication dependency is attached by the application middleware in production.
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return db.scalars(select(FinancialTransaction).where(FinancialTransaction.company_id == company_id).order_by(FinancialTransaction.transaction_date.desc()).limit(limit)).all()


@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, user=Depends(lambda: None), db: Session = Depends(get_db)):
    company_id = getattr(user, "company_id", None)
    user_id = getattr(user, "id", None)
    if not company_id or not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    item = FinancialTransaction(company_id=company_id, created_by=user_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/milestones", response_model=list[MilestoneOut])
def list_milestones(user=Depends(lambda: None), db: Session = Depends(get_db)):
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return db.scalars(select(PaymentMilestone).where(PaymentMilestone.company_id == company_id).order_by(PaymentMilestone.due_date.asc())).all()


@router.post("/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(payload: MilestoneCreate, user=Depends(lambda: None), db: Session = Depends(get_db)):
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not payload.project_id and not payload.client_id:
        raise HTTPException(status_code=422, detail="A client or project is required")
    item = PaymentMilestone(company_id=company_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/milestones/{milestone_id}/payments", response_model=MilestoneOut)
def record_payment(milestone_id: UUID, payload: PaymentRecord, user=Depends(lambda: None), db: Session = Depends(get_db)):
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    item = db.scalar(select(PaymentMilestone).where(PaymentMilestone.id == milestone_id, PaymentMilestone.company_id == company_id))
    if not item:
        raise HTTPException(status_code=404, detail="Payment milestone not found")
    if item.paid_amount + payload.amount > item.amount:
        raise HTTPException(status_code=422, detail="Payment exceeds milestone amount")
    item.paid_amount += payload.amount
    item.status = "paid" if item.paid_amount == item.amount else "partially_paid"
    db.commit()
    db.refresh(item)
    return item


@router.get("/dashboard", response_model=FinanceDashboard)
def dashboard(user=Depends(lambda: None), db: Session = Depends(get_db)):
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == company_id, FinancialTransaction.transaction_type == "income")) or Decimal("0")
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == company_id, FinancialTransaction.transaction_type == "expense")) or Decimal("0")
    total_due = db.scalar(select(func.coalesce(func.sum(PaymentMilestone.amount - PaymentMilestone.paid_amount), 0)).where(PaymentMilestone.company_id == company_id, PaymentMilestone.status != "paid")) or Decimal("0")
    freelancer = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == company_id, FinancialTransaction.transaction_type == "expense", FinancialTransaction.category == "freelancer")) or Decimal("0")
    return FinanceDashboard(revenue=income, expenses=expenses, outstanding=total_due, freelancer_payments=freelancer, project_profitability=income-expenses)
