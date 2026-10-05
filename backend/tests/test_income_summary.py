from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Category, CategoryGroup, Transaction
from app.reporting import income_for_month


def _account(db):
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db.add(account)
    db.flush()
    return account


def test_income_for_month_sums_only_income_category_transactions(db_session):
    account = _account(db_session)
    income = Category(name="Income", group=CategoryGroup.INCOME)
    groceries = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([income, groceries])
    db_session.flush()

    db_session.add_all(
        [
            Transaction(
                account_id=account.id,
                date=date(2026, 9, 2),
                description="Payroll",
                amount=Decimal("2500.00"),
                external_id="a",
                category_id=income.id,
            ),
            Transaction(
                account_id=account.id,
                date=date(2026, 9, 15),
                description="Side gig",
                amount=Decimal("300.00"),
                external_id="b",
                category_id=income.id,
            ),
            Transaction(
                account_id=account.id,
                date=date(2026, 9, 5),
                description="Groceries",
                amount=Decimal("-150.00"),
                external_id="c",
                category_id=groceries.id,
            ),
            Transaction(
                account_id=account.id,
                date=date(2026, 8, 2),
                description="Payroll",
                amount=Decimal("2500.00"),
                external_id="d",
                category_id=income.id,
            ),
        ]
    )
    db_session.commit()

    assert income_for_month(db_session, 2026, 9) == Decimal("2800.00")


def test_income_for_month_is_zero_with_no_income_transactions(db_session):
    assert income_for_month(db_session, 2026, 9) == Decimal("0")


def test_income_summary_via_api(client):
    account = client.post(
        "/accounts",
        json={"name": "Checking", "institution": "Bank of America", "type": "checking"},
    ).json()
    categories = client.get("/categories").json()
    income_id = next(c["id"] for c in categories if c["name"] == "Income")

    client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-09-02",
            "description": "Payroll",
            "amount": "2500.00",
            "category_id": income_id,
        },
    )

    response = client.get("/reports/income-summary", params={"year": 2026, "month": 9})
    assert response.status_code == 200
    body = response.json()
    assert body["income"] == "2500.00"
