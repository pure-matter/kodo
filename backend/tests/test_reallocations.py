from decimal import Decimal

import pytest

from app.models import Category, CategoryGroup
from app.reporting import budget_summary, create_reallocation, list_reallocations


def _category_id_by_name(client, name):
    categories = client.get("/categories").json()
    return next(c["id"] for c in categories if c["name"] == name)


def test_reallocation_shifts_budgeted_without_touching_spent(db_session):
    from_cat = Category(name="Entertainment", group=CategoryGroup.WANTS, monthly_budget=Decimal("150"))
    to_cat = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([from_cat, to_cat])
    db_session.commit()

    create_reallocation(db_session, 2026, 9, from_cat.id, to_cat.id, Decimal("50"))

    rows = {r["category_name"]: r for r in budget_summary(db_session, 2026, 9)}
    assert rows["Entertainment"]["budgeted"] == Decimal("100")
    assert rows["Groceries"]["budgeted"] == Decimal("450")
    assert rows["Entertainment"]["spent"] == Decimal("0")
    assert rows["Groceries"]["spent"] == Decimal("0")


def test_reallocation_only_applies_to_its_own_month(db_session):
    from_cat = Category(name="Entertainment", group=CategoryGroup.WANTS, monthly_budget=Decimal("150"))
    to_cat = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([from_cat, to_cat])
    db_session.commit()

    create_reallocation(db_session, 2026, 9, from_cat.id, to_cat.id, Decimal("50"))

    rows = {r["category_name"]: r for r in budget_summary(db_session, 2026, 10)}
    assert rows["Entertainment"]["budgeted"] == Decimal("150")
    assert rows["Groceries"]["budgeted"] == Decimal("400")


def test_reallocation_into_a_category_with_no_budget_gives_it_one(db_session):
    from_cat = Category(name="Entertainment", group=CategoryGroup.WANTS, monthly_budget=Decimal("150"))
    to_cat = Category(name="Misc", group=CategoryGroup.WANTS, monthly_budget=None)
    db_session.add_all([from_cat, to_cat])
    db_session.commit()

    create_reallocation(db_session, 2026, 9, from_cat.id, to_cat.id, Decimal("30"))

    rows = {r["category_name"]: r for r in budget_summary(db_session, 2026, 9)}
    assert rows["Misc"]["budgeted"] == Decimal("30")


def test_create_reallocation_rejects_same_from_and_to(db_session):
    cat = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add(cat)
    db_session.commit()

    with pytest.raises(ValueError):
        create_reallocation(db_session, 2026, 9, cat.id, cat.id, Decimal("10"))


def test_create_reallocation_rejects_non_positive_amount(db_session):
    from_cat = Category(name="Entertainment", group=CategoryGroup.WANTS, monthly_budget=Decimal("150"))
    to_cat = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([from_cat, to_cat])
    db_session.commit()

    with pytest.raises(ValueError):
        create_reallocation(db_session, 2026, 9, from_cat.id, to_cat.id, Decimal("0"))


def test_create_reallocation_rejects_non_spend_category(db_session):
    income = Category(name="Income", group=CategoryGroup.INCOME)
    groceries = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([income, groceries])
    db_session.commit()

    with pytest.raises(ValueError):
        create_reallocation(db_session, 2026, 9, income.id, groceries.id, Decimal("10"))


def test_list_reallocations_returns_only_that_month(db_session):
    from_cat = Category(name="Entertainment", group=CategoryGroup.WANTS, monthly_budget=Decimal("150"))
    to_cat = Category(name="Groceries", group=CategoryGroup.NEEDS, monthly_budget=Decimal("400"))
    db_session.add_all([from_cat, to_cat])
    db_session.commit()

    create_reallocation(db_session, 2026, 9, from_cat.id, to_cat.id, Decimal("50"))
    create_reallocation(db_session, 2026, 10, from_cat.id, to_cat.id, Decimal("20"))

    assert len(list_reallocations(db_session, 2026, 9)) == 1
    assert len(list_reallocations(db_session, 2026, 10)) == 1


def test_reallocation_api_end_to_end(client):
    from_id = _category_id_by_name(client, "Entertainment")
    to_id = _category_id_by_name(client, "Groceries")

    response = client.post(
        "/reports/reallocations",
        json={"year": 2026, "month": 9, "from_category_id": from_id, "to_category_id": to_id, "amount": "50"},
    )
    assert response.status_code == 201
    realloc = response.json()
    assert realloc["from_category_name"] == "Entertainment"
    assert realloc["to_category_name"] == "Groceries"

    listed = client.get("/reports/reallocations", params={"year": 2026, "month": 9}).json()
    assert len(listed) == 1

    summary = {r["category_name"]: r for r in client.get("/reports/budget-summary", params={"year": 2026, "month": 9}).json()}
    assert summary["Groceries"]["budgeted"] == "450.00"

    assert client.delete(f"/reports/reallocations/{realloc['id']}").status_code == 204
    assert client.get("/reports/reallocations", params={"year": 2026, "month": 9}).json() == []


def test_reallocation_api_rejects_invalid_category(client):
    to_id = _category_id_by_name(client, "Groceries")
    response = client.post(
        "/reports/reallocations",
        json={"year": 2026, "month": 9, "from_category_id": 999, "to_category_id": to_id, "amount": "50"},
    )
    assert response.status_code == 400
