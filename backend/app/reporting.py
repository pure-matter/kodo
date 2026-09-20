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
    MonthlySavingsSummary,
    MonthlySpendSummary,
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


def _category_totals_for_month(db: Session, year: int, month: int) -> list[dict]:
    """budget_summary() for one month, with each row's spend swapped for an
    archived MonthlySpendSummary value when one exists - so a month that's
    been archived (and had its transactions deleted) still reports its real
    total instead of a live-computed zero."""
    archived = {
        s.category_id: s.spent
        for s in db.query(MonthlySpendSummary).filter_by(year=year, month=month)
    }
    rows = budget_summary(db, year, month)
    for row in rows:
        row["spent"] = archived.get(row["category_id"], row["spent"])
    return rows


def _savings_contributed_for_month(db: Session, year: int, month: int) -> Decimal:
    """Total contributed across all savings allocations for one month,
    preferring an archived MonthlySavingsSummary value the same way
    _category_totals_for_month does for spend categories."""
    archived = {
        s.allocation_id: s.contributed
        for s in db.query(MonthlySavingsSummary).filter_by(year=year, month=month)
    }
    return sum(
        (archived.get(row["allocation_id"], row["contributed"]) for row in savings_progress(db, year, month)),
        Decimal("0"),
    )


def archive_month(db: Session, year: int, month: int) -> list[dict]:
    """Snapshots each Needs/Wants category's total spend, and each savings
    allocation's contribution, for (year, month) - updating in place if
    already archived - then deletes the underlying Transaction rows dated
    in that month across all accounts to keep the table from growing
    forever.

    Only ever called from an explicit user action - never automatically.
    Re-importing a statement for an archived month will not detect
    duplicates (the dedup rows are gone), which is a known, accepted
    trade-off of clearing the data rather than a bug.
    """
    summary_rows = budget_summary(db, year, month)

    for row in summary_rows:
        existing = (
            db.query(MonthlySpendSummary)
            .filter_by(category_id=row["category_id"], year=year, month=month)
            .first()
        )
        if existing:
            existing.spent = row["spent"]
        else:
            db.add(
                MonthlySpendSummary(
                    category_id=row["category_id"],
                    year=year,
                    month=month,
                    spent=row["spent"],
                )
            )

    for row in savings_progress(db, year, month):
        existing = (
            db.query(MonthlySavingsSummary)
            .filter_by(allocation_id=row["allocation_id"], year=year, month=month)
            .first()
        )
        if existing:
            existing.contributed = row["contributed"]
        else:
            db.add(
                MonthlySavingsSummary(
                    allocation_id=row["allocation_id"],
                    year=year,
                    month=month,
                    contributed=row["contributed"],
                )
            )
    db.flush()

    db.query(Transaction).filter(
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month,
    ).delete(synchronize_session=False)

    db.commit()
    return summary_rows


def monthly_history(db: Session, months: int) -> list[dict]:
    """Per-category spend for each of the last `months` calendar months
    (most recent first), preferring an archived total when one exists for
    that month - so a month you haven't archived yet still shows up
    correctly, and one you have doesn't drop to zero."""
    today = date.today()
    year, month = today.year, today.month
    results = []

    for _ in range(months):
        for row in _category_totals_for_month(db, year, month):
            results.append(
                {
                    "year": year,
                    "month": month,
                    "category_id": row["category_id"],
                    "category_name": row["category_name"],
                    "spent": row["spent"],
                }
            )
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return results


def bucket_monthly_history(db: Session, months: int) -> list[dict]:
    """Needs/Wants/Savings totals for each of the last `months` calendar
    months (most recent first) - the same archived-vs-live preference as
    monthly_history, rolled up to bucket level instead of per-category."""
    today = date.today()
    year, month = today.year, today.month
    results = []

    for _ in range(months):
        category_rows = _category_totals_for_month(db, year, month)
        needs = sum(
            (r["spent"] for r in category_rows if r["group"] == CategoryGroup.NEEDS), Decimal("0")
        )
        wants = sum(
            (r["spent"] for r in category_rows if r["group"] == CategoryGroup.WANTS), Decimal("0")
        )
        savings = _savings_contributed_for_month(db, year, month)
        results.append({"year": year, "month": month, "needs": needs, "wants": wants, "savings": savings})
        month -= 1
        if month == 0:
            month = 12
            year -= 1

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
