from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BudgetReallocation
from ..reporting import (
    archive_month,
    available_months,
    budget_summary,
    bucket_monthly_history,
    create_reallocation,
    income_for_month,
    list_reallocations,
    monthly_history,
)
from ..schemas import (
    ArchiveMonthRequest,
    AvailableMonthOut,
    BucketHistoryItem,
    BudgetReallocationCreate,
    BudgetReallocationOut,
    BudgetSummaryItem,
    IncomeSummaryOut,
    MonthlyHistoryItem,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _reallocation_to_out(realloc: BudgetReallocation) -> dict:
    return {
        "id": realloc.id,
        "year": realloc.year,
        "month": realloc.month,
        "from_category_id": realloc.from_category_id,
        "from_category_name": realloc.from_category.name,
        "to_category_id": realloc.to_category_id,
        "to_category_name": realloc.to_category.name,
        "amount": realloc.amount,
    }


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


@router.get("/reallocations", response_model=list[BudgetReallocationOut])
def get_reallocations(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: Session = Depends(get_db),
):
    return [_reallocation_to_out(r) for r in list_reallocations(db, year, month)]


@router.post("/reallocations", response_model=BudgetReallocationOut, status_code=201)
def post_reallocation(payload: BudgetReallocationCreate, db: Session = Depends(get_db)):
    try:
        realloc = create_reallocation(
            db,
            payload.year,
            payload.month,
            payload.from_category_id,
            payload.to_category_id,
            payload.amount,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _reallocation_to_out(realloc)


@router.delete("/reallocations/{reallocation_id}", status_code=204)
def delete_reallocation(reallocation_id: int, db: Session = Depends(get_db)):
    realloc = db.get(BudgetReallocation, reallocation_id)
    if realloc is None:
        raise HTTPException(404, "Reallocation not found")
    db.delete(realloc)
    db.commit()
