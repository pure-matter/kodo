from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..reporting import (
    archive_month,
    available_months,
    budget_summary,
    bucket_monthly_history,
    income_for_month,
    monthly_history,
)
from ..schemas import (
    ArchiveMonthRequest,
    AvailableMonthOut,
    BucketHistoryItem,
    BudgetSummaryItem,
    IncomeSummaryOut,
    MonthlyHistoryItem,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/budget-summary", response_model=list[BudgetSummaryItem])
def get_budget_summary(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: Session = Depends(get_db),
):
    return budget_summary(db, year, month)


@router.get("/available-months", response_model=list[AvailableMonthOut])
def get_available_months(db: Session = Depends(get_db)):
    return available_months(db)


@router.get("/income-summary", response_model=IncomeSummaryOut)
def get_income_summary(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: Session = Depends(get_db),
):
    return {"year": year, "month": month, "income": income_for_month(db, year, month)}


@router.get("/monthly-history", response_model=list[MonthlyHistoryItem])
def get_monthly_history(months: int = 6, db: Session = Depends(get_db)):
    return monthly_history(db, months)


@router.get("/bucket-history", response_model=list[BucketHistoryItem])
def get_bucket_history(months: int = 6, db: Session = Depends(get_db)):
    return bucket_monthly_history(db, months)


@router.post("/archive-month", response_model=list[BudgetSummaryItem])
def post_archive_month(payload: ArchiveMonthRequest, db: Session = Depends(get_db)):
    """Snapshots the month's per-category totals, then deletes that
    month's raw transactions. Explicit and irreversible - the frontend
    should confirm with the user before calling this."""
    return archive_month(db, payload.year, payload.month)
