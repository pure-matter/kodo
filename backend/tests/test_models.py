from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Account, AccountType, Category, CategoryGroup, Transaction


def test_create_account_and_transaction(db_session):
    account = Account(name="Checking", institution="Bank of America", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    txn = Transaction(
        account_id=account.id,
        date=date(2026, 9, 1),
        description="Sample",
        amount=Decimal("-10.00"),
        external_id="abc123",
    )
    db_session.add(txn)
    db_session.commit()

    assert txn.id is not None
    assert txn.category_id is None


def test_duplicate_external_id_within_account_is_rejected(db_session):
    account = Account(name="Checking", institution="Bank of America", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    db_session.add(
        Transaction(
            account_id=account.id,
            date=date(2026, 9, 1),
            description="First",
            amount=Decimal("-10.00"),
            external_id="dup",
        )
    )
    db_session.commit()

    db_session.add(
        Transaction(
            account_id=account.id,
            date=date(2026, 9, 2),
            description="Second",
            amount=Decimal("-20.00"),
            external_id="dup",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_external_id_allowed_across_different_accounts(db_session):
    checking = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    savings = Account(name="Savings", institution="BoA", type=AccountType.SAVINGS)
    db_session.add_all([checking, savings])
    db_session.flush()

    db_session.add_all(
        [
            Transaction(
                account_id=checking.id,
                date=date(2026, 9, 1),
                description="A",
                amount=Decimal("-10.00"),
                external_id="shared",
            ),
            Transaction(
                account_id=savings.id,
                date=date(2026, 9, 1),
                description="B",
                amount=Decimal("-10.00"),
                external_id="shared",
            ),
        ]
    )
    db_session.commit()  # should not raise


def test_category_budget_is_optional(db_session):
    category = Category(name="Misc", group=CategoryGroup.WANTS, monthly_budget=None)
    db_session.add(category)
    db_session.commit()
    assert category.monthly_budget is None
