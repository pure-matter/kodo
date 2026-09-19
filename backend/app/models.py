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
