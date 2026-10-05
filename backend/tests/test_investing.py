from datetime import date, timedelta
from decimal import Decimal

from app.investing import (
    goal_contributed,
    holding_current_value,
    holding_projected_value,
    required_monthly_contribution,
)
from app.models import GoalContribution, Holding, InvestmentType, SavingsGoal


def test_holding_current_value_uses_live_price_when_present():
    holding = Holding(
        investment_type=InvestmentType.STOCK,
        name="Apple",
        symbol="AAPL",
        shares=Decimal("10"),
        cost_basis=Decimal("100"),
        current_price=Decimal("150"),
    )
    assert holding_current_value(holding) == Decimal("1500.00")


def test_holding_current_value_falls_back_to_cost_basis_with_no_price_yet():
    holding = Holding(
        investment_type=InvestmentType.STOCK,
        name="Apple",
        symbol="AAPL",
        shares=Decimal("10"),
        cost_basis=Decimal("100"),
    )
    assert holding_current_value(holding) == Decimal("1000.00")


def test_holding_current_value_uses_manual_value_for_non_share_assets():
    holding = Holding(
        investment_type=InvestmentType.REAL_ESTATE,
        name="Land",
        cost_basis=Decimal("50000"),
        manual_value=Decimal("65000"),
    )
    assert holding_current_value(holding) == Decimal("65000")


def test_holding_current_value_prefers_manual_value_over_cost_basis_even_with_shares():
    """RSUs or any ticker-less, share-based holding: a $0 cost basis (the
    normal case for an RSU grant) combined with the shares x cost_basis
    fallback used to silently produce $0 - or, worse, a nonsense number if
    cost_basis held something else - even when the user had entered their
    own current value. The manual override must win once it's set."""
    holding = Holding(
        investment_type=InvestmentType.STOCK,
        name="Apple RSUs",
        shares=Decimal("50"),
        cost_basis=Decimal("0"),
        manual_value=Decimal("9500"),
    )
    assert holding_current_value(holding) == Decimal("9500")


def test_holding_projected_value_compounds_with_apy():
    holding = Holding(
        investment_type=InvestmentType.REAL_ESTATE,
        name="Land",
        cost_basis=Decimal("50000"),
        manual_value=Decimal("50000"),
        manual_apy=Decimal("10"),
        projection_years=2,
    )
    # 50000 * 1.1^2 = 60500
    assert holding_projected_value(holding) == Decimal("60500")


def test_holding_projected_value_falls_back_to_stored_estimate_without_apy():
    holding = Holding(
        investment_type=InvestmentType.STOCK,
        name="Apple",
        cost_basis=Decimal("1000"),
        target_projected_value=Decimal("2500"),
    )
    assert holding_projected_value(holding) == Decimal("2500")


def test_goal_contributed_sums_logged_contributions():
    goal = SavingsGoal(name="Emergency fund", target_amount=Decimal("10000"))
    goal.contributions = [
        GoalContribution(date=date(2026, 1, 1), amount=Decimal("500")),
        GoalContribution(date=date(2026, 2, 1), amount=Decimal("500")),
    ]
    assert goal_contributed(goal) == Decimal("1000")


def test_required_monthly_contribution_without_apy_is_simple_division():
    today = date(2026, 1, 1)
    goal = SavingsGoal(
        name="Vacation", target_amount=Decimal("1200"), target_date=date(2026, 7, 1)
    )
    goal.contributions = []
    # 6 months remaining, no contributions yet -> 200/month
    assert required_monthly_contribution(goal, today) == Decimal("200.00")


def test_required_monthly_contribution_accounts_for_existing_progress():
    today = date(2026, 1, 1)
    goal = SavingsGoal(
        name="Vacation", target_amount=Decimal("1200"), target_date=date(2026, 7, 1)
    )
    goal.contributions = [GoalContribution(date=date(2025, 12, 1), amount=Decimal("600"))]
    assert required_monthly_contribution(goal, today) == Decimal("100.00")


def test_required_monthly_contribution_returns_none_without_target_date():
    goal = SavingsGoal(name="Vacation", target_amount=Decimal("1200"))
    goal.contributions = []
    assert required_monthly_contribution(goal) is None


def test_required_monthly_contribution_returns_none_when_date_already_passed():
    today = date(2026, 1, 1)
    goal = SavingsGoal(
        name="Vacation", target_amount=Decimal("1200"), target_date=date(2025, 12, 1)
    )
    goal.contributions = []
    assert required_monthly_contribution(goal, today) is None


def test_required_monthly_contribution_is_zero_once_target_met():
    today = date(2026, 1, 1)
    goal = SavingsGoal(
        name="Vacation", target_amount=Decimal("1200"), target_date=date(2026, 7, 1)
    )
    goal.contributions = [GoalContribution(date=date(2025, 12, 1), amount=Decimal("1200"))]
    assert required_monthly_contribution(goal, today) == Decimal("0.00")


def test_required_monthly_contribution_with_apy_is_lower_than_without():
    today = date(2026, 1, 1)
    target_date = today + timedelta(days=365 * 3)
    no_apy_goal = SavingsGoal(name="Retirement top-up", target_amount=Decimal("36000"), target_date=target_date)
    no_apy_goal.contributions = [GoalContribution(date=today, amount=Decimal("0"))]
    with_apy_goal = SavingsGoal(
        name="Retirement top-up",
        target_amount=Decimal("36000"),
        target_date=target_date,
        manual_apy=Decimal("7"),
    )
    with_apy_goal.contributions = [GoalContribution(date=today, amount=Decimal("10000"))]

    without = required_monthly_contribution(no_apy_goal, today)
    with_growth = required_monthly_contribution(with_apy_goal, today)
    assert with_growth < without
