from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    LOAN = "loan"
    INVESTMENT = "investment"


class CategoryGroup(str, enum.Enum):
    NEEDS = "needs"
    WANTS = "wants"
    INCOME = "income"
    # Money moving between the user's own accounts (credit card payments,
    # contributions into savings/investment accounts). Excluded from spend
    # and income totals so it isn't double-counted.
    TRANSFER = "transfer"


class InvestmentType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    RETIREMENT_401K = "retirement_401k"
    ROTH_IRA = "roth_ira"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class RecurringFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    institution: Mapped[str] = mapped_column(String(120))
    type: Mapped[AccountType] = mapped_column(Enum(AccountType))
    # Key into the ingestion parser registry (e.g. "boa_checking", "amex").
    # None means this account has no parser (GTBank, MSU, investments,
    # loans) and its transactions/balances are entered by hand instead.
    parser_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(
        back_populates="account"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    group: Mapped[CategoryGroup] = mapped_column(Enum(CategoryGroup))
    monthly_budget: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    rules: Mapped[list["CategoryRule"]] = relationship(back_populates="category")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")


class BudgetReallocation(Base):
    """A one-month shift of budgeted (not spent) dollars from one category
    to another - e.g. "Entertainment had room, Groceries went over, move
    $50." Purely a budget-math adjustment: never touches transactions, and
    only affects the `budgeted` figure for the (year, month) it's logged
    against, via reporting.budget_summary."""

    __tablename__ = "budget_reallocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column()
    month: Mapped[int] = mapped_column()
    from_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    to_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    from_category: Mapped["Category"] = relationship(foreign_keys=[from_category_id])
    to_category: Mapped["Category"] = relationship(foreign_keys=[to_category_id])


class CategoryRule(Base):
    """Matches a transaction description substring (case-insensitive) to a
    category. Rules are applied in ascending `priority` order and the first
    match wins, so more specific rules should get a lower number."""

    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    priority: Mapped[int] = mapped_column(default=100)

    category: Mapped["Category"] = relationship(back_populates="rules")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "external_id", name="uq_account_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # Dedup key from the source file (parser-generated hash or the bank's
    # own reference number). Unique per account, not globally.
    external_id: Mapped[str] = mapped_column(String(64))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    # Category hint from the source file itself (e.g. Amex's own category),
    # kept for seeding/improving rules even after the transaction has its
    # own category assigned.
    source_category_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Manually reviewed by the user (separate from categorization - a
    # transaction can be correctly categorized by a rule and still be
    # unreviewed). Always starts False, including on import, so newly
    # imported transactions are clearly distinguishable from ones already
    # looked at.
    is_reviewed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship(back_populates="transactions")


class SavingsAllocation(Base):
    """A recurring monthly savings/investment target for one destination
    (e.g. "put $850/month into Fidelity"), matched against the description
    of Transfer-category transactions to compute progress."""

    __tablename__ = "savings_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    monthly_target: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # Substring matched against transaction descriptions to attribute a
    # transfer to this allocation. Nullable until a known pattern is set.
    match_pattern: Mapped[str | None] = mapped_column(String(200), nullable=True)


class MonthlySavingsSummary(Base):
    """A frozen per-allocation contributed total for one month, captured
    alongside MonthlySpendSummary by the same "archive month" action, so
    the Savings bucket in history views doesn't silently drop to zero once
    that month's Transfer transactions are deleted."""

    __tablename__ = "monthly_savings_summaries"
    __table_args__ = (
        UniqueConstraint("allocation_id", "year", "month", name="uq_allocation_year_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    allocation_id: Mapped[int] = mapped_column(ForeignKey("savings_allocations.id"))
    year: Mapped[int] = mapped_column()
    month: Mapped[int] = mapped_column()
    contributed: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    allocation: Mapped["SavingsAllocation"] = relationship()


class MonthlySpendSummary(Base):
    """A frozen per-category total for one month, captured by an explicit
    "archive month" action (see reporting.archive_month) so spending
    history survives even after that month's raw Transaction rows are
    deleted to keep the table from growing forever. Never written
    automatically - only when the user asks to archive."""

    __tablename__ = "monthly_spend_summaries"
    __table_args__ = (
        UniqueConstraint("category_id", "year", "month", name="uq_category_year_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    year: Mapped[int] = mapped_column()
    month: Mapped[int] = mapped_column()
    spent: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    category: Mapped["Category"] = relationship()


class Holding(Base):
    """A single investment position: a stock/ETF lot, a retirement account,
    a piece of real estate, etc. Priced two ways depending on what it is:
    `shares` + `current_price` (kept fresh via Finnhub for stock/etf) for
    market-traded things, or `manual_value` for anything else (land, a
    401k balance) that the user updates by hand."""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    investment_type: Mapped[InvestmentType] = mapped_column(Enum(InvestmentType))
    name: Mapped[str] = mapped_column(String(120))
    # Ticker symbol, only present (and only usable for a Finnhub price
    # refresh) for stock/etf holdings.
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shares: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    # Price per share (when `shares` is set) or total value (when it isn't)
    # at the time this was bought/opened.
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Per-share market price, refreshed on demand from Finnhub.
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    current_price_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Manually-entered current total value, for holdings Finnhub can't price
    # (real estate, a 401k/Roth balance with no ticker).
    manual_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Expected annual growth rate (percent, e.g. 7 for 7%) used to project
    # this holding's value forward when there's no live price trend to
    # extrapolate from.
    manual_apy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    projection_years: Mapped[int | None] = mapped_column(nullable=True)
    # The user's own stored estimate of this holding's value at
    # `projection_years` out - used as-is when `manual_apy` isn't set, shown
    # alongside the APY-computed figure when it is.
    target_projected_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    account: Mapped["Account"] = relationship()


class SavingsGoal(Base):
    """A long-term savings target (e.g. "$10k emergency fund by 2028"),
    distinct from SavingsAllocation's recurring monthly targets. Progress is
    the sum of its GoalContribution rows, logged by hand the same way a
    BalanceSnapshot is."""

    __tablename__ = "savings_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    # Expected annual growth rate on money already saved toward this goal
    # (e.g. a HYSA's APY), factored into the required-monthly-savings calc.
    manual_apy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Set once contributions reach target_amount. Achieved goals drop off
    # the dashboard and get a "met" highlight in the Looking Ahead tab
    # instead of just disappearing.
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    linked_account: Mapped["Account | None"] = relationship()
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", order_by="GoalContribution.date"
    )


class GoalContribution(Base):
    """One logged deposit toward a SavingsGoal, on a given date - the raw
    data behind both the goal's progress total and its contributions-over-
    time graph."""

    __tablename__ = "goal_contributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("savings_goals.id"))
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    goal: Mapped["SavingsGoal"] = relationship(back_populates="contributions")


class RecurringInvestment(Base):
    """A standing plan to contribute toward a goal or holding on a
    schedule (e.g. "$200/month into Roth IRA"). Doesn't itself create
    GoalContribution rows - it's a declared plan shown in the Looking Ahead
    tab and used to project whether a goal will hit its target date, not an
    automatic transaction feed."""

    __tablename__ = "recurring_investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency))
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("savings_goals.id"), nullable=True)
    holding_id: Mapped[int | None] = mapped_column(ForeignKey("holdings.id"), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

    goal: Mapped["SavingsGoal | None"] = relationship()
    holding: Mapped["Holding | None"] = relationship()


class UninvestedCash(Base):
    """A point-in-time "cash sitting uninvested" balance for one account -
    same snapshot-over-time shape as BalanceSnapshot, kept separate since
    it's a different question (idle cash within an investment account,
    not the account's total balance)."""

    __tablename__ = "uninvested_cash"
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_uninvested_account_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    account: Mapped["Account"] = relationship()


class BalanceSnapshot(Base):
    """A point-in-time balance for an account. Used for accounts with no
    transaction feed (investments, loans) to compute net worth, and can
    also be recorded periodically for imported accounts as a sanity check."""

    __tablename__ = "balance_snapshots"
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_account_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    date: Mapped[date] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    account: Mapped["Account"] = relationship(back_populates="balance_snapshots")
