from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EXPENSE_CATEGORIES = {"software", "marketing", "operating", "freelancer"}
INCOME_CATEGORIES = {"client_payment", "revenue", "other_income"}


class TransactionCreate(BaseModel):
    transaction_type: str = Field(pattern="^(income|expense)$")
    category: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    transaction_date: date
    reference_type: str | None = Field(default=None, max_length=32)
    reference_id: UUID | None = None
    project_id: UUID | None = None
    client_id: UUID | None = None
    freelancer_id: UUID | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str, info):
        transaction_type = info.data.get("transaction_type")
        allowed = EXPENSE_CATEGORIES if transaction_type == "expense" else INCOME_CATEGORIES
        if value not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return value


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
    notes: str | None = None


class ProjectProfitability(BaseModel):
    project_id: UUID
    project_name: str
    revenue: Decimal
    expenses: Decimal
    profitability: Decimal


class FinanceDashboard(BaseModel):
    revenue: Decimal
    expenses: Decimal
    outstanding: Decimal
    freelancer_payments: Decimal
    project_profitability: Decimal
    software_expenses: Decimal
    marketing_expenses: Decimal
    operating_expenses: Decimal
    project_reports: list[ProjectProfitability] = []
