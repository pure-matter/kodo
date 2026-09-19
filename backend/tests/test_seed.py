from decimal import Decimal

from app.models import Category, CategoryGroup, SavingsAllocation
from app.seed import seed_all


def test_seed_creates_all_master_categories(db_session):
    seed_all(db_session)
    names = {c.name for c in db_session.query(Category).all()}
    # 25 spend categories from the master list + Income + Transfer
    assert len(names) == 27
    assert "Income" in names
    assert "Transfer" in names


def test_needs_budget_total_matches_sheet(db_session):
    seed_all(db_session)
    needs = db_session.query(Category).filter_by(group=CategoryGroup.NEEDS).all()
    total = sum((c.monthly_budget or Decimal("0")) for c in needs)
    assert total == Decimal("3305.00")


def test_savings_allocation_targets_match_sheet(db_session):
    seed_all(db_session)
    allocations = db_session.query(SavingsAllocation).all()
    total = sum(a.monthly_target for a in allocations)
    assert total == Decimal("1600.00")
    assert {a.name for a in allocations} == {"Robinhood", "LC", "GMB", "FID", "Kalifa"}


def test_seed_is_idempotent(db_session):
    seed_all(db_session)
    seed_all(db_session)  # running twice should not duplicate rows
    assert db_session.query(Category).count() == 27
    assert db_session.query(SavingsAllocation).count() == 5
