"""Turns a transaction's description (and optional source-provided category
hint) into a Category id.

Two layers, tried in order:
  1. CategoryRule matches (user-learned rules and seeded rules), by
     ascending priority - lower number wins. A rule matches when its
     pattern is a case-insensitive substring of the description.
  2. A source-provided category hint (currently only Amex sets this),
     mapped through a small, deliberately conservative lookup table.

Anything neither layer resolves comes back as None (uncategorized) for the
user to assign by hand - which in turn calls learn_rule() to remember the
choice.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Category, CategoryRule

DEFAULT_LEARNED_RULE_PRIORITY = 10
DEFAULT_SEEDED_RULE_PRIORITY = 100

# Amex's own per-transaction categories, used only when no CategoryRule
# matched. Kept small and conservative: "Restaurant-Bar & Café" covers both
# restaurants and coffee shops, so it defaults to Eating Out rather than
# guessing Coffee/Dessert - recategorizing a specific coffee shop merchant
# creates a learned rule (see learn_rule) that wins next time.
AMEX_HINT_TO_CATEGORY = {
    "Merchandise & Supplies-Groceries": "Groceries",
    "Transportation-Fuel": "Gas (Car)",
    "Transportation-Tolls & Fees": "Car Expenses",
    "Restaurant-Bar & Café": "Eating Out",
    "Restaurant-Restaurant": "Eating Out",
    "Other-Miscellaneous": "Misc",
}


def match_rule(description: str, rules: list[CategoryRule]) -> int | None:
    description_lower = description.lower()
    for rule in sorted(rules, key=lambda r: r.priority):
        if rule.pattern.lower() in description_lower:
            return rule.category_id
    return None


def categorize_transaction(
    db: Session, description: str, source_category_hint: str | None
) -> int | None:
    rules = db.query(CategoryRule).all()
    category_id = match_rule(description, rules)
    if category_id is not None:
        return category_id

    if source_category_hint and source_category_hint in AMEX_HINT_TO_CATEGORY:
        category = (
            db.query(Category)
            .filter_by(name=AMEX_HINT_TO_CATEGORY[source_category_hint])
            .first()
        )
        if category:
            return category.id

    return None


def learn_rule(
    db: Session,
    pattern: str,
    category_id: int,
    priority: int = DEFAULT_LEARNED_RULE_PRIORITY,
) -> CategoryRule:
    """Records a user's manual recategorization as a rule so future imports
    of the same merchant categorize automatically. Learned rules default to
    a lower (higher-precedence) priority than seeded ones, so a user's own
    correction always wins over a generic seeded/hint-based guess."""
    existing = (
        db.query(CategoryRule).filter_by(pattern=pattern, category_id=category_id).first()
    )
    if existing:
        return existing

    rule = CategoryRule(pattern=pattern, category_id=category_id, priority=priority)
    db.add(rule)
    db.commit()
    return rule
