from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..reporting import budget_summary
from ..schemas import BudgetSummaryItem

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/budget-summary", response_model=list[BudgetSummaryItem])
def get_budget_summary(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: Session = Depends(get_db),
):
    return budget_summary(db, year, month)
