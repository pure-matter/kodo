from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..categorization import learn_rule
from ..db import get_db
from ..models import Account, Category, Transaction
from ..schemas import BulkReviewRequest, TransactionCategoryUpdate, TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    uncategorized_only: bool = False,
    reviewed: bool | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if uncategorized_only:
        query = query.filter(Transaction.category_id.is_(None))
    if reviewed is not None:
        query = query.filter(Transaction.is_reviewed == reviewed)
    return query.order_by(Transaction.date.desc()).all()


@router.post("", response_model=TransactionOut, status_code=201)
def create_manual_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    """For accounts with no parser (GTBank, MSU, etc.) - transactions
    entered by hand. Each gets a random external_id since there's no
    source file to dedup against."""
    account = db.get(Account, payload.account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    transaction = Transaction(**payload.model_dump(), external_id=f"manual:{uuid4().hex}")
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/bulk-review", response_model=list[TransactionOut])
def bulk_review_transactions(payload: BulkReviewRequest, db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.id.in_(payload.transaction_ids)).all()
    for transaction in transactions:
        transaction.is_reviewed = payload.reviewed
    db.commit()
    for transaction in transactions:
        db.refresh(transaction)
    return transactions


@router.patch("/{transaction_id}", response_model=TransactionOut)
def recategorize_transaction(
    transaction_id: int, payload: TransactionCategoryUpdate, db: Session = Depends(get_db)
):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(404, "Transaction not found")
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(404, "Category not found")

    transaction.category_id = payload.category_id
    db.commit()

    if payload.create_rule:
        if not payload.pattern:
            raise HTTPException(400, "pattern is required when create_rule is true")
        learn_rule(db, pattern=payload.pattern, category_id=payload.category_id)

    db.refresh(transaction)
    return transaction
