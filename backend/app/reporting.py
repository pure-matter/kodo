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

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from .investing import goal_contributed, holding_current_value
from .models import (
    Account,
    AccountType,
    BalanceSnapshot,
    BudgetReallocation,
    Category,
    CategoryGroup,
    Holding,
    MonthlySavingsSummary,
    MonthlySpendSummary,
    SavingsAllocation,
    SavingsGoal,
    Transaction,
    UninvestedCash,
)

_ASSET_TYPES = {AccountType.CHECKING, AccountType.SAVINGS, AccountType.INVESTMENT}


def _reallocation_deltas(db: Session, year: int, month: int) -> dict[int, Decimal]:
    """Net budget shift per category for one month: positive for a category
    that received a reallocation, negative for one that gave money away.
    Used to adjust budget_summary's `budgeted` figure - reallocations never
    touch transactions or a category's own monthly_budget."""
    deltas: dict[int, Decimal] = {}
    for realloc in db.query(BudgetReallocation).filter_by(year=year, month=month):
        deltas[realloc.to_category_id] = deltas.get(realloc.to_category_id, Decimal("0")) + realloc.amount
        deltas[realloc.from_category_id] = deltas.get(realloc.from_category_id, Decimal("0")) - realloc.amount
    return deltas


def budget_summary(db: Session, year: int, month: int) -> list[dict]:
    categories = (
        db.query(Category)
        .filter(Category.group.in_([CategoryGroup.NEEDS, CategoryGroup.WANTS]))
        .all()
    )
    deltas = _reallocation_deltas(db, year, month)

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

        delta = deltas.get(category.id, Decimal("0"))
        if category.monthly_budget is None and delta == 0:
            budgeted = None
        else:
            budgeted = (category.monthly_budget or Decimal("0")) + delta

        results.append(
            {
                "category_id": category.id,
                "category_name": category.name,
                "group": category.group,
                "budgeted": budgeted,
                "spent": spent,
            }
        )
    return results


def create_reallocation(
    db: Session, year: int, month: int, from_category_id: int, to_category_id: int, amount: Decimal
) -> BudgetReallocation:
    if from_category_id == to_category_id:
        raise ValueError("Can't reallocate a category's budget to itself.")
    if amount <= 0:
        raise ValueError("Reallocation amount must be positive.")

    spendable = {CategoryGroup.NEEDS, CategoryGroup.WANTS}
    for category_id in (from_category_id, to_category_id):
        category = db.get(Category, category_id)
        if category is None:
            raise ValueError(f"Category {category_id} not found.")
        if category.group not in spendable:
            raise ValueError(f'"{category.name}" isn\'t a Needs/Wants category - reallocation only applies there.')

    realloc = BudgetReallocation(
        year=year,
        month=month,
        from_category_id=from_category_id,
        to_category_id=to_category_id,
        amount=amount,
    )
    db.add(realloc)
    db.commit()
    db.refresh(realloc)
    return realloc


def list_reallocations(db: Session, year: int, month: int) -> list[BudgetReallocation]:
    return (
        db.query(BudgetReallocation)
        .filter_by(year=year, month=month)
        .order_by(BudgetReallocation.created_at)
        .all()
    )


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


def income_for_month(db: Session, year: int, month: int) -> Decimal:
    """Total income (stored as positive amounts, unlike spend) for one
    month - backs the Dashboard's spend-vs-income card. Not archive-aware
    like category/savings totals are, since archiving only snapshots
    Needs/Wants spend and savings contributions - an archived month's
    income reads as 0, same trade-off as its raw transactions."""
    total = (
        db.query(func.sum(Transaction.amount))
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Category.group == CategoryGroup.INCOME,
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
        .scalar()
    )
    return total or Decimal("0")


def available_months(db: Session) -> list[dict]:
    """Distinct (year, month) pairs that still have live transactions,
    most recent first. A month that's been archived has had its
    transactions deleted, so it naturally drops out of this list - the
    Dashboard's month picker uses it to only offer months it can show a
    real (non-zero) live summary for."""
    rows = (
        db.query(extract("year", Transaction.date), extract("month", Transaction.date))
        .distinct()
        .all()
    )
    months = [{"year": int(year), "month": int(month)} for year, month in rows]
    months.sort(key=lambda m: (m["year"], m["month"]), reverse=True)
    return months


def net_worth(db: Session) -> dict:
    """Assets are sourced per account, preferring the most specific data
    available: an investment account with Holdings logged uses their live
    total (+ any uninvested cash) instead of a manual BalanceSnapshot, since
    the Holdings/Investments tab is the more accurate, detailed picture once
    it's in use. Accounts with no holdings fall back to BalanceSnapshot,
    same as checking/savings/credit/loan always have.

    Savings goal contributions are added separately, but only for goals
    with no linked_account_id - a goal linked to an account is assumed to
    be money already sitting in (and counted via) that account, so adding
    it again here would double-count it."""
    assets = Decimal("0")
    liabilities = Decimal("0")

    holdings_by_account: dict[int, list[Holding]] = {}
    for holding in db.query(Holding).all():
        holdings_by_account.setdefault(holding.account_id, []).append(holding)

    latest_uninvested_by_account: dict[int, Decimal] = {}
    for entry in db.query(UninvestedCash).order_by(UninvestedCash.date.desc()):
        latest_uninvested_by_account.setdefault(entry.account_id, entry.amount)

    for account in db.query(Account).all():
        account_holdings = holdings_by_account.get(account.id)
        if account.type == AccountType.INVESTMENT and account_holdings:
            total = sum((holding_current_value(h) for h in account_holdings), Decimal("0"))
            total += latest_uninvested_by_account.get(account.id, Decimal("0"))
            assets += total
            continue

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

    for goal in db.query(SavingsGoal).all():
        if goal.linked_account_id is None:
            assets += goal_contributed(goal)

    return {
        "as_of": date.today(),
        "assets": assets,
        "liabilities": liabilities,
        "net_worth": assets - liabilities,
    }
