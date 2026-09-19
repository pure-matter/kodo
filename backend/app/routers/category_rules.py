from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Category, CategoryRule
from ..schemas import CategoryRuleCreate, CategoryRuleOut

router = APIRouter(prefix="/category-rules", tags=["category-rules"])


@router.get("", response_model=list[CategoryRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(CategoryRule).order_by(CategoryRule.priority).all()


@router.post("", response_model=CategoryRuleOut, status_code=201)
def create_rule(payload: CategoryRuleCreate, db: Session = Depends(get_db)):
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(404, "Category not found")
    rule = CategoryRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
