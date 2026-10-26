from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    transaction_type: str = Field(pattern="^(income|expense)$")
    category: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    transaction_date: date
    reference_type: str | None = None
    reference_id: UUID | None = None
    notes: str | None = None


class TransactionOut(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    status: str


class MilestoneCreate(BaseModel):
    project_id: UUID | None = None
    client_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0)
    due_date: date | None = None
    notes: str | None = None


class MilestoneOut(MilestoneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    status: str
    paid_amount: Decimal


class PaymentRecord(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: date


class FinanceDashboard(BaseModel):
    revenue: Decimal
    expenses: Decimal
    outstanding: Decimal
    freelancer_payments: Decimal
    project_profitability: Decimal
