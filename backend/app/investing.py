"""Calculations for the Looking Ahead tab: holding values/projections,
savings goal progress and required-contribution math, and portfolio
breakdowns. Mirrors reporting.py's shape (pure functions over a Session)
but kept separate since it's a distinct domain (investments/goals rather
than spend/budget)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from .models import Account, GoalContribution, Holding, SavingsGoal

TWO_PLACES = Decimal("0.01")


def holding_current_value(holding: Holding) -> Decimal:
    """Market value for a priced holding (shares x current price, falling
    back to cost basis if no price has been fetched yet), or the
    hand-entered value for anything else."""
    if holding.shares is not None:
        price = holding.current_price if holding.current_price is not None else holding.cost_basis
        return (holding.shares * price).quantize(TWO_PLACES)
    if holding.manual_value is not None:
        return holding.manual_value
    return holding.cost_basis


def holding_projected_value(holding: Holding) -> Decimal | None:
    """The value a holding is expected to reach at `projection_years` out.
    Computed by compounding its current value at `manual_apy` when set;
    otherwise falls back to the user's own stored estimate, since not every
    asset has a growth rate worth guessing at (e.g. a specific stock pick)."""
    if holding.manual_apy is not None and holding.projection_years is not None:
        rate = float(holding.manual_apy) / 100
        current = float(holding_current_value(holding))
        projected = current * ((1 + rate) ** holding.projection_years)
        return Decimal(str(round(projected, 2)))
    return holding.target_projected_value


def holding_to_out(holding: Holding) -> dict:
    return {
        "id": holding.id,
        "account_id": holding.account_id,
        "investment_type": holding.investment_type,
        "name": holding.name,
        "symbol": holding.symbol,
        "shares": holding.shares,
        "cost_basis": holding.cost_basis,
        "purchase_date": holding.purchase_date,
        "current_price": holding.current_price,
        "current_price_updated_at": holding.current_price_updated_at,
        "manual_value": holding.manual_value,
        "manual_apy": holding.manual_apy,
        "projection_years": holding.projection_years,
        "target_projected_value": holding.target_projected_value,
        "current_value": holding_current_value(holding),
        "computed_projected_value": holding_projected_value(holding),
    }


def goal_contributed(goal: SavingsGoal) -> Decimal:
    return sum((c.amount for c in goal.contributions), Decimal("0"))


def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def required_monthly_contribution(goal: SavingsGoal, today: date | None = None) -> Decimal | None:
    """The flat monthly deposit needed to hit `target_amount` by
    `target_date`. Returns None when there's no target date (nothing to
    solve for) or it's already passed/this month (no runway left to spread
    payments over).

    When `manual_apy` is set, money already saved is assumed to keep
    earning that rate until the target date (future value of a lump sum),
    and the remaining gap is solved as the payment on an ordinary annuity
    at the equivalent monthly rate - standard savings-goal math, not
    exact-to-the-penny compounding, which is fine for a planning estimate.
    """
    if goal.target_date is None:
        return None
    today = today or date.today()
    months = _months_between(today, goal.target_date)
    if months <= 0:
        return None

    contributed = goal_contributed(goal)
    target = goal.target_amount

    if goal.manual_apy is not None:
        monthly_rate = (1 + float(goal.manual_apy) / 100) ** (1 / 12) - 1
        grown_contributions = float(contributed) * ((1 + monthly_rate) ** months)
        remaining = float(target) - grown_contributions
        if remaining <= 0:
            return Decimal("0.00")
        if monthly_rate == 0:
            payment = remaining / months
        else:
            payment = remaining * monthly_rate / (((1 + monthly_rate) ** months) - 1)
        return Decimal(str(round(payment, 2)))

    remaining = target - contributed
    if remaining <= 0:
        return Decimal("0.00")
    return (remaining / months).quantize(TWO_PLACES)


def goal_to_out(goal: SavingsGoal, today: date | None = None) -> dict:
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": goal.target_amount,
        "target_date": goal.target_date,
        "linked_account_id": goal.linked_account_id,
        "manual_apy": goal.manual_apy,
        "created_at": goal.created_at,
        "achieved_at": goal.achieved_at,
        "contributed": goal_contributed(goal),
        "required_monthly_contribution": required_monthly_contribution(goal, today),
    }


def maybe_mark_achieved(goal: SavingsGoal) -> None:
    """Sets achieved_at the first time contributions reach the target.
    Never unsets it - a goal that's met stays met even if the linked
    account balance later dips, since the point is to record that it was
    reached, not to track a live balance against the target forever."""
    if goal.achieved_at is None and goal_contributed(goal) >= goal.target_amount:
        goal.achieved_at = datetime.utcnow()


def portfolio_breakdown(db: Session) -> dict:
    holdings = db.query(Holding).all()
    total = sum((holding_current_value(h) for h in holdings), Decimal("0"))

    by_type_totals: dict[str, Decimal] = {}
    by_account_totals: dict[str, Decimal] = {}
    account_names = {a.id: a.name for a in db.query(Account).all()}

    for holding in holdings:
        value = holding_current_value(holding)
        type_key = holding.investment_type.value
        by_type_totals[type_key] = by_type_totals.get(type_key, Decimal("0")) + value
        account_name = account_names.get(holding.account_id, "Unknown account")
        by_account_totals[account_name] = by_account_totals.get(account_name, Decimal("0")) + value

    def to_slices(totals: dict[str, Decimal]) -> list[dict]:
        slices = []
        for label, value in totals.items():
            percent = (value / total * 100).quantize(TWO_PLACES) if total else Decimal("0")
            slices.append({"label": label, "value": value, "percent_of_total": percent})
        return sorted(slices, key=lambda s: s["value"], reverse=True)

    return {
        "by_type": to_slices(by_type_totals),
        "by_account": to_slices(by_account_totals),
        "total_portfolio_value": total,
    }
