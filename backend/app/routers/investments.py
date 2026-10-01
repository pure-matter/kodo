from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..investing import (
    goal_to_out,
    holding_to_out,
    maybe_mark_achieved,
    portfolio_breakdown,
)
from ..market_data import MarketDataError, fetch_quote
from ..models import (
    Account,
    GoalContribution,
    Holding,
    RecurringInvestment,
    SavingsGoal,
    UninvestedCash,
)
from ..schemas import (
    GoalContributionCreate,
    GoalContributionOut,
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
    LookingAheadSummaryOut,
    RecurringInvestmentCreate,
    RecurringInvestmentOut,
    RecurringInvestmentUpdate,
    SavingsGoalCreate,
    SavingsGoalOut,
    SavingsGoalUpdate,
    UninvestedCashCreate,
    UninvestedCashOut,
)

router = APIRouter(tags=["investments"])


# --- Holdings -----------------------------------------------------------


@router.get("/holdings", response_model=list[HoldingOut])
def list_holdings(db: Session = Depends(get_db)):
    return [holding_to_out(h) for h in db.query(Holding).all()]


@router.post("/holdings", response_model=HoldingOut, status_code=201)
def create_holding(payload: HoldingCreate, db: Session = Depends(get_db)):
    if db.get(Account, payload.account_id) is None:
        raise HTTPException(404, "Account not found")
    holding = Holding(**payload.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding_to_out(holding)


@router.patch("/holdings/{holding_id}", response_model=HoldingOut)
def update_holding(holding_id: int, payload: HoldingUpdate, db: Session = Depends(get_db)):
    holding = db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(404, "Holding not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(holding, field, value)
    db.commit()
    db.refresh(holding)
    return holding_to_out(holding)


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(404, "Holding not found")
    db.query(RecurringInvestment).filter_by(holding_id=holding_id).update({"holding_id": None})
    db.delete(holding)
    db.commit()


@router.post("/holdings/{holding_id}/refresh-price", response_model=HoldingOut)
def refresh_holding_price(holding_id: int, db: Session = Depends(get_db)):
    holding = db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(404, "Holding not found")
    if not holding.symbol:
        raise HTTPException(400, "This holding has no ticker symbol to look up.")

    try:
        price = fetch_quote(holding.symbol)
    except MarketDataError as exc:
        raise HTTPException(502, str(exc)) from exc

    holding.current_price = Decimal(str(price))
    holding.current_price_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(holding)
    return holding_to_out(holding)


# --- Savings goals --------------------------------------------------------


@router.get("/savings-goals", response_model=list[SavingsGoalOut])
def list_goals(db: Session = Depends(get_db)):
    return [goal_to_out(g) for g in db.query(SavingsGoal).all()]


@router.post("/savings-goals", response_model=SavingsGoalOut, status_code=201)
def create_goal(payload: SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = SavingsGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_to_out(goal)


@router.patch("/savings-goals/{goal_id}", response_model=SavingsGoalOut)
def update_goal(goal_id: int, payload: SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(404, "Savings goal not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal_to_out(goal)


@router.delete("/savings-goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(404, "Savings goal not found")
    db.query(RecurringInvestment).filter_by(goal_id=goal_id).update({"goal_id": None})
    db.query(GoalContribution).filter_by(goal_id=goal_id).delete()
    db.delete(goal)
    db.commit()


@router.get("/savings-goals/{goal_id}/contributions", response_model=list[GoalContributionOut])
def list_contributions(goal_id: int, db: Session = Depends(get_db)):
    if db.get(SavingsGoal, goal_id) is None:
        raise HTTPException(404, "Savings goal not found")
    return (
        db.query(GoalContribution)
        .filter_by(goal_id=goal_id)
        .order_by(GoalContribution.date)
        .all()
    )


@router.post(
    "/savings-goals/{goal_id}/contributions", response_model=GoalContributionOut, status_code=201
)
def add_contribution(goal_id: int, payload: GoalContributionCreate, db: Session = Depends(get_db)):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(404, "Savings goal not found")
    contribution = GoalContribution(goal_id=goal_id, **payload.model_dump())
    db.add(contribution)
    db.flush()
    db.refresh(goal)
    maybe_mark_achieved(goal)
    db.commit()
    db.refresh(contribution)
    return contribution


# --- Recurring investments ------------------------------------------------


@router.get("/recurring-investments", response_model=list[RecurringInvestmentOut])
def list_recurring(db: Session = Depends(get_db)):
    return db.query(RecurringInvestment).all()


@router.post("/recurring-investments", response_model=RecurringInvestmentOut, status_code=201)
def create_recurring(payload: RecurringInvestmentCreate, db: Session = Depends(get_db)):
    recurring = RecurringInvestment(**payload.model_dump())
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return recurring


@router.patch("/recurring-investments/{recurring_id}", response_model=RecurringInvestmentOut)
def update_recurring(
    recurring_id: int, payload: RecurringInvestmentUpdate, db: Session = Depends(get_db)
):
    recurring = db.get(RecurringInvestment, recurring_id)
    if recurring is None:
        raise HTTPException(404, "Recurring investment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(recurring, field, value)
    db.commit()
    db.refresh(recurring)
    return recurring


@router.delete("/recurring-investments/{recurring_id}", status_code=204)
def delete_recurring(recurring_id: int, db: Session = Depends(get_db)):
    recurring = db.get(RecurringInvestment, recurring_id)
    if recurring is None:
        raise HTTPException(404, "Recurring investment not found")
    db.delete(recurring)
    db.commit()


# --- Uninvested cash --------------------------------------------------------


@router.get("/accounts/{account_id}/uninvested-cash", response_model=list[UninvestedCashOut])
def list_uninvested_cash(account_id: int, db: Session = Depends(get_db)):
    return (
        db.query(UninvestedCash)
        .filter_by(account_id=account_id)
        .order_by(UninvestedCash.date.desc())
        .all()
    )


@router.post("/accounts/{account_id}/uninvested-cash", response_model=UninvestedCashOut)
def log_uninvested_cash(
    account_id: int, payload: UninvestedCashCreate, db: Session = Depends(get_db)
):
    """Same upsert-by-date behavior as balance snapshots - logging again
    for a date you've already logged corrects it instead of erroring."""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    existing = (
        db.query(UninvestedCash).filter_by(account_id=account_id, date=payload.date).first()
    )
    if existing:
        existing.amount = payload.amount
        db.commit()
        db.refresh(existing)
        return existing

    entry = UninvestedCash(account_id=account_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --- Summary ----------------------------------------------------------------


@router.get("/looking-ahead/summary", response_model=LookingAheadSummaryOut)
def looking_ahead_summary(db: Session = Depends(get_db)):
    goals = db.query(SavingsGoal).all()
    active_goals = [goal_to_out(g) for g in goals if g.achieved_at is None]
    achieved_goals = [goal_to_out(g) for g in goals if g.achieved_at is not None]

    holdings = [holding_to_out(h) for h in db.query(Holding).all()]
    breakdown = portfolio_breakdown(db)

    latest_cash_by_account: dict[int, UninvestedCash] = {}
    for entry in db.query(UninvestedCash).order_by(UninvestedCash.date.desc()).all():
        latest_cash_by_account.setdefault(entry.account_id, entry)

    return {
        "goals": active_goals,
        "achieved_goals": achieved_goals,
        "holdings": holdings,
        "by_type": breakdown["by_type"],
        "by_account": breakdown["by_account"],
        "uninvested_cash": list(latest_cash_by_account.values()),
        "recurring_investments": db.query(RecurringInvestment).filter_by(active=True).all(),
        "total_portfolio_value": breakdown["total_portfolio_value"],
    }
