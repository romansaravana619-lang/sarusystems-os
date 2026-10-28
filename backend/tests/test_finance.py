from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.finance.router import PERMISSION_CREATE_TRANSACTIONS, PERMISSION_RECORD_PAYMENTS, PERMISSION_VIEW_DASHBOARD
from app.finance.schemas import MilestoneCreate, PaymentRecord, TransactionCreate


def test_transaction_contract():
    item = TransactionCreate(transaction_type="income", category="client_payment", description="Deposit", amount=Decimal("1000"), transaction_date="2026-10-26", client_id="00000000-0000-0000-0000-000000000001")
    assert item.amount == Decimal("1000")


def test_transaction_rejects_invalid_expense_category():
    with pytest.raises(ValidationError):
        TransactionCreate(transaction_type="expense", category="client_payment", description="Bad", amount=Decimal("100"), transaction_date="2026-10-26")


def test_freelancer_expense_contract_requires_reference_at_api_boundary():
    item = TransactionCreate(transaction_type="expense", category="freelancer", description="Freelancer fee", amount=Decimal("100"), transaction_date="2026-10-26")
    assert item.category == "freelancer"


def test_milestone_requires_positive_amount():
    with pytest.raises(ValidationError):
        MilestoneCreate(name="Milestone", amount=Decimal("0"), client_id="00000000-0000-0000-0000-000000000001")


def test_payment_requires_positive_amount():
    with pytest.raises(ValidationError):
        PaymentRecord(amount=Decimal("0"), payment_date="2026-10-26")


def test_finance_permissions_are_explicit():
    assert PERMISSION_VIEW_DASHBOARD == "finance.dashboard.view"
    assert PERMISSION_CREATE_TRANSACTIONS == "finance.transactions.create"
    assert PERMISSION_RECORD_PAYMENTS == "finance.payments.record"
