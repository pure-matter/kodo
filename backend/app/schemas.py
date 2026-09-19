from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .models import AccountType, CategoryGroup


class AccountCreate(BaseModel):
    name: str
    institution: str
    type: AccountType
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
