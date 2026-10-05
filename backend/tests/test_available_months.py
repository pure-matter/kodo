from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Category, CategoryGroup, Transaction
from app.reporting import archive_month, available_months


def _account(db):
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db.add(account)
    db.flush()
    return account


def _category(db):
    category = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db.add(category)
    db.flush()
    return category


def test_available_months_lists_distinct_months_most_recent_first(db_session):
    account = _account(db_session)
    category = _category(db_session)
    db_session.add_all(
        [
            Transaction(
                account_id=account.id,
                date=date(2026, 8, 5),
                description="Store A",
                amount=Decimal("-10"),
                external_id="a",
                category_id=category.id,
            ),
            Transaction(
                account_id=account.id,
                date=date(2026, 9, 5),
                description="Store B",
                amount=Decimal("-10"),
                external_id="b",
                category_id=category.id,
            ),
            Transaction(
                account_id=account.id,
                date=date(2026, 9, 20),
                description="Store C",
                amount=Decimal("-10"),
                external_id="c",
                category_id=category.id,
            ),
        ]
    )
    db_session.commit()

    assert available_months(db_session) == [
        {"year": 2026, "month": 9},
        {"year": 2026, "month": 8},
    ]


def test_available_months_excludes_archived_months(db_session):
    account = _account(db_session)
    category = _category(db_session)
    db_session.add(
        Transaction(
            account_id=account.id,
            date=date(2026, 8, 5),
            description="Store A",
            amount=Decimal("-10"),
            external_id="a",
            category_id=category.id,
        )
    )
    db_session.commit()

    archive_month(db_session, 2026, 8)

    assert available_months(db_session) == []


def test_available_months_empty_when_no_transactions(db_session):
    assert available_months(db_session) == []
