from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .models import AccountType, CategoryGroup, InvestmentType, RecurringFrequency


class AccountCreate(BaseModel):
    name: str
    institution: str
    type: AccountType
    parser_type: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    institution: str | None = None
    type: AccountType | None = None
    parser_type: str | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    institution: str
    type: AccountType
    parser_type: str | None
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str
    group: CategoryGroup
    monthly_budget: Decimal | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    group: CategoryGroup | None = None
    monthly_budget: Decimal | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group: CategoryGroup
    monthly_budget: Decimal | None


class CategoryRuleCreate(BaseModel):
    pattern: str
    category_id: int
    priority: int = 100


class CategoryRuleUpdate(BaseModel):
    pattern: str | None = None
    category_id: int | None = None
    priority: int | None = None


class CategoryRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pattern: str
    category_id: int
    priority: int


class TransactionCreate(BaseModel):
    account_id: int
    date: date
    description: str
    amount: Decimal
    category_id: int | None = None


class TransactionCategoryUpdate(BaseModel):
    category_id: int
    create_rule: bool = False
    pattern: str | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    date: date
    description: str
    amount: Decimal
    category_id: int | None
    source_category_hint: str | None
    is_reviewed: bool


class BulkReviewRequest(BaseModel):
    transaction_ids: list[int]
    reviewed: bool = True


class ImportSummaryOut(BaseModel):
    total_in_file: int
    imported: int
    skipped_duplicates: int


class SavingsAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    monthly_target: Decimal
    match_pattern: str | None


class SavingsProgressOut(BaseModel):
    allocation_id: int
    name: str
    monthly_target: Decimal
    contributed: Decimal


class BalanceSnapshotCreate(BaseModel):
    date: date
    balance: Decimal


class BalanceSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    date: date
    balance: Decimal


class NetWorthOut(BaseModel):
    as_of: date
    assets: Decimal
    liabilities: Decimal
    net_worth: Decimal


class BudgetSummaryItem(BaseModel):
    category_id: int
    category_name: str
    group: CategoryGroup
    budgeted: Decimal | None
    spent: Decimal


class ArchiveMonthRequest(BaseModel):
    year: int
    month: int


class AvailableMonthOut(BaseModel):
    year: int
    month: int


class IncomeSummaryOut(BaseModel):
    year: int
    month: int
    income: Decimal


class BudgetReallocationCreate(BaseModel):
    year: int
    month: int
    from_category_id: int
    to_category_id: int
    amount: Decimal


class BudgetReallocationOut(BaseModel):
    id: int
    year: int
    month: int
    from_category_id: int
    from_category_name: str
    to_category_id: int
    to_category_name: str
    amount: Decimal


class MonthlyHistoryItem(BaseModel):
    year: int
    month: int
    category_id: int
    category_name: str
    spent: Decimal


class BucketHistoryItem(BaseModel):
    year: int
    month: int
    needs: Decimal
    wants: Decimal
    savings: Decimal


class HoldingCreate(BaseModel):
    account_id: int
    investment_type: InvestmentType
    name: str
    symbol: str | None = None
    shares: Decimal | None = None
    cost_basis: Decimal
    purchase_date: date | None = None
    manual_value: Decimal | None = None
    manual_apy: Decimal | None = None
    projection_years: int | None = None
    target_projected_value: Decimal | None = None


class HoldingUpdate(BaseModel):
    account_id: int | None = None
    investment_type: InvestmentType | None = None
    name: str | None = None
    symbol: str | None = None
    shares: Decimal | None = None
    cost_basis: Decimal | None = None
    purchase_date: date | None = None
    manual_value: Decimal | None = None
    manual_apy: Decimal | None = None
    projection_years: int | None = None
    target_projected_value: Decimal | None = None


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    investment_type: InvestmentType
    name: str
    symbol: str | None
    shares: Decimal | None
    cost_basis: Decimal
    purchase_date: date | None
    current_price: Decimal | None
    current_price_updated_at: datetime | None
    manual_value: Decimal | None
    manual_apy: Decimal | None
    projection_years: int | None
    target_projected_value: Decimal | None
    current_value: Decimal
    computed_projected_value: Decimal | None


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: Decimal
    target_date: date | None = None
    linked_account_id: int | None = None
    manual_apy: Decimal | None = None


class SavingsGoalUpdate(BaseModel):
    name: str | None = None
    target_amount: Decimal | None = None
    target_date: date | None = None
    linked_account_id: int | None = None
    manual_apy: Decimal | None = None


class SavingsGoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_amount: Decimal
    target_date: date | None
    linked_account_id: int | None
    manual_apy: Decimal | None
    created_at: datetime
    achieved_at: datetime | None
    contributed: Decimal
    required_monthly_contribution: Decimal | None


class GoalContributionCreate(BaseModel):
    date: date
    amount: Decimal


class GoalContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int
    date: date
    amount: Decimal


class RecurringInvestmentCreate(BaseModel):
    name: str
    amount: Decimal
    frequency: RecurringFrequency
    goal_id: int | None = None
    holding_id: int | None = None
    active: bool = True


class RecurringInvestmentUpdate(BaseModel):
    name: str | None = None
    amount: Decimal | None = None
    frequency: RecurringFrequency | None = None
    goal_id: int | None = None
    holding_id: int | None = None
    active: bool | None = None


class RecurringInvestmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Decimal
    frequency: RecurringFrequency
    goal_id: int | None
    holding_id: int | None
    active: bool


class UninvestedCashCreate(BaseModel):
    date: date
    amount: Decimal


class UninvestedCashOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    date: date
    amount: Decimal


class PortfolioSliceOut(BaseModel):
    label: str
    value: Decimal
    percent_of_total: Decimal


class LookingAheadSummaryOut(BaseModel):
    goals: list[SavingsGoalOut]
    achieved_goals: list[SavingsGoalOut]
    holdings: list[HoldingOut]
    by_type: list[PortfolioSliceOut]
    by_account: list[PortfolioSliceOut]
    uninvested_cash: list[UninvestedCashOut]
    recurring_investments: list[RecurringInvestmentOut]
    total_portfolio_value: Decimal
