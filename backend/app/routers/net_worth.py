from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Account, BalanceSnapshot
from ..reporting import net_worth as compute_net_worth
from ..schemas import BalanceSnapshotCreate, BalanceSnapshotOut, NetWorthOut

router = APIRouter(tags=["net-worth"])


@router.get("/net-worth", response_model=NetWorthOut)
def get_net_worth(db: Session = Depends(get_db)):
    return compute_net_worth(db)


@router.post(
    "/accounts/{account_id}/balance-snapshots",
    response_model=BalanceSnapshotOut,
    status_code=201,
)
def create_balance_snapshot(
    account_id: int, payload: BalanceSnapshotCreate, db: Session = Depends(get_db)
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    snapshot = BalanceSnapshot(account_id=account_id, **payload.model_dump())
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
