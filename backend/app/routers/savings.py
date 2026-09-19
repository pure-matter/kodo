from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SavingsAllocation
from ..reporting import savings_progress
from ..schemas import SavingsAllocationOut, SavingsProgressOut

router = APIRouter(prefix="/savings-allocations", tags=["savings"])


@router.get("", response_model=list[SavingsAllocationOut])
def list_allocations(db: Session = Depends(get_db)):
    return db.query(SavingsAllocation).all()


@router.get("/progress", response_model=list[SavingsProgressOut])
def get_progress(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: Session = Depends(get_db),
):
    return savings_progress(db, year, month)
