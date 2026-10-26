from decimal import Decimal

from app.finance.schemas import MilestoneCreate, PaymentRecord, TransactionCreate


def test_transaction_contract():
    item = TransactionCreate(transaction_type="income", category="client_payment", description="Deposit", amount=Decimal("1000"), transaction_date="2026-10-26")
    assert item.amount == Decimal("1000")


def test_milestone_requires_positive_amount():
    try:
        MilestoneCreate(name="Milestone", amount=Decimal("0"), client_id="00000000-0000-0000-0000-000000000001")
    except Exception:
        return
    raise AssertionError("non-positive milestone amount must be rejected")


def test_payment_requires_positive_amount():
    try:
        PaymentRecord(amount=Decimal("0"), payment_date="2026-10-26")
    except Exception:
        return
    raise AssertionError("non-positive payment must be rejected")
