"""Read-side queries that turn raw transactions into the numbers the app is
actually for: spend vs. budget per category, savings progress, net worth.

Net worth and balances are intentionally sourced only from BalanceSnapshot,
for every account type including checking/credit. Deriving a live balance
from a running sum of transactions would need a starting-balance anchor we
don't have yet, so for now "what's my balance" always means "the last
balance you told us about," same as investments/loans.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import extract
from sqlalchemy.orm import Session

from .models import (
    Account,
    AccountType,
    BalanceSnapshot,
    Category,
    CategoryGroup,
    SavingsAllocation,
    Transaction,
)

_ASSET_TYPES = {AccountType.CHECKING, AccountType.SAVINGS, AccountType.INVESTMENT}


def budget_summary(db: Session, year: int, month: int) -> list[dict]:
    categories = (
        db.query(Category)
        .filter(Category.group.in_([CategoryGroup.NEEDS, CategoryGroup.WANTS]))
        .all()
    )

    results = []
    for category in categories:
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.category_id == category.id,
                extract("year", Transaction.date) == year,
                extract("month", Transaction.date) == month,
            )
            .all()
        )
        # Spend is stored negative (money out); report it as a positive
        # "amount spent" since that's what a budget comparison expects.
        spent = -sum((t.amount for t in transactions), Decimal("0"))
        results.append(
            {
                "category_id": category.id,
                "category_name": category.name,
                "group": category.group,
                "budgeted": category.monthly_budget,
                "spent": spent,
            }
        )
    return results


def savings_progress(db: Session, year: int, month: int) -> list[dict]:
    transfer_category = db.query(Category).filter_by(name="Transfer").first()
    allocations = db.query(SavingsAllocation).all()

    results = []
    for allocation in allocations:
        contributed = Decimal("0")
        if allocation.match_pattern and transfer_category:
            pattern_lower = allocation.match_pattern.lower()
            matches = (
                db.query(Transaction)
                .filter(
                    Transaction.category_id == transfer_category.id,
                    extract("year", Transaction.date) == year,
                    extract("month", Transaction.date) == month,
                )
                .all()
            )
            outgoing = sum(
                (
                    t.amount
                    for t in matches
                    if t.amount < 0 and pattern_lower in t.description.lower()
                ),
                Decimal("0"),
            )
            contributed = -outgoing  # stored negative (money leaving); report as positive
        results.append(
            {
                "allocation_id": allocation.id,
                "name": allocation.name,
                "monthly_target": allocation.monthly_target,
                "contributed": contributed,
            }
        )
    return results


def net_worth(db: Session) -> dict:
    assets = Decimal("0")
    liabilities = Decimal("0")

    for account in db.query(Account).all():
        latest = (
            db.query(BalanceSnapshot)
            .filter_by(account_id=account.id)
            .order_by(BalanceSnapshot.date.desc())
            .first()
        )
        if latest is None:
            continue
        if account.type in _ASSET_TYPES:
            assets += latest.balance
        else:
            liabilities += latest.balance

    return {
        "as_of": date.today(),
        "assets": assets,
        "liabilities": liabilities,
        "net_worth": assets - liabilities,
    }
