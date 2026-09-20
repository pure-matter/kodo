from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Category, CategoryRule
from ..schemas import CategoryRuleCreate, CategoryRuleOut, CategoryRuleUpdate

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


@router.patch("/{rule_id}", response_model=CategoryRuleOut)
def update_rule(rule_id: int, payload: CategoryRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(CategoryRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")

    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise HTTPException(404, "Category not found")

    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(CategoryRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()
