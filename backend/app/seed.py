"""Seeds categories, monthly budgets, and savings allocations from the
user's existing budget spreadsheet.

A few labels in the spreadsheet didn't match the canonical category list
1:1, so they were reconciled by hand:
  - "Health" (budget sheet) -> Medical (category list)
  - "Phone bill" -> Phone
  - "Gas" -> Gas (Car)
  - "Car (tolls, mechanic)" -> Car Expenses
  - "Clothes" -> Clothing
  - "Home" -> Home Items
  - "Short Travel" -> Travel
  - "Going Out" and "Quran classes" have no corresponding category in the
    canonical list and were dropped (both had $0 or duplicate budgets
    already covered by "Eating Out" / "Education"); add them back as real
    categories if that was wrong.

Savings allocations' match_pattern is only set where the actual bank
statements showed a matching description (Robinhood, FID); the others
(LC, GMB, Kalifa) are seeded with no pattern until we see a real
transaction to match against.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from .categorization import DEFAULT_SEEDED_RULE_PRIORITY
from .models import Category, CategoryGroup, CategoryRule, SavingsAllocation

# (name, monthly_budget or None)
NEEDS_CATEGORIES: list[tuple[str, Decimal | None]] = [
    ("Housing", Decimal("1500")),
    ("Utilities", Decimal("300")),
    ("Phone", Decimal("230")),
    ("Zakat", Decimal("250")),
    ("Education", Decimal("250")),
    ("Medical", None),
    ("Internet", Decimal("65")),
    ("Groceries", Decimal("400")),
    ("Gas (Car)", Decimal("150")),
    ("Car Expenses", Decimal("160")),
]

WANTS_CATEGORIES: list[tuple[str, Decimal | None]] = [
    ("Self Care", Decimal("100")),
    ("Entertainment", Decimal("150")),
    ("Clothing", Decimal("100")),
    ("Subscriptions", Decimal("30")),
    ("Athletics", Decimal("120")),
    ("Eating Out", Decimal("100")),
    ("Coffee/Dessert", Decimal("40")),
    ("Home Items", Decimal("250")),
    ("Books", None),
    ("Gifts", None),
    ("Family", Decimal("500")),
    ("Misc", None),
    ("Travel", None),
    ("Business", Decimal("50")),
    ("Fees", None),
]

SAVINGS_ALLOCATIONS: list[tuple[str, Decimal, str | None]] = [
    ("Robinhood", Decimal("150"), "ROBINHOOD"),
    ("LC", Decimal("400"), None),
    ("GMB", Decimal("150"), None),
    ("FID", Decimal("850"), "FID BKG SVC"),
    ("Kalifa", Decimal("50"), None),
]

# (pattern, target category name) - all evidence-backed from the user's
# real BoA/Amex statements, not guesses. Money moving between the user's
# own accounts (credit card payments, brokerage/investment debits) goes to
# Transfer so it isn't double-counted as spend once the receiving side
# (e.g. the Amex statement itself) is also imported.
TRANSFER_RULE_PATTERNS = [
    "AMERICAN EXPRESS",
    "CITI CARD ONLINE",
    "MOBILE PAYMENT - THANK YOU",  # Amex's own label for a payment received
    "ONLINE/MOBILE RECURRING FROM CHK",  # BoA credit card receiving a payment
    "ONLINE SCHEDULED PAYMENT TO ACCT#",  # BoA-to-BoA account payment
    "ROBINHOOD",
    "FID BKG SVC",
]

INCOME_RULE_PATTERNS = [
    "APPLE INC.",
]

HOUSING_RULE_PATTERNS = [
    "MTG PYMTS",  # mortgage payment, regardless of servicer name
]


def seed_categories(db: Session) -> None:
    if db.query(Category).count() > 0:
        return

    for name, budget in NEEDS_CATEGORIES:
        db.add(Category(name=name, group=CategoryGroup.NEEDS, monthly_budget=budget))
    for name, budget in WANTS_CATEGORIES:
        db.add(Category(name=name, group=CategoryGroup.WANTS, monthly_budget=budget))
    db.add(Category(name="Income", group=CategoryGroup.INCOME, monthly_budget=None))
    db.add(Category(name="Transfer", group=CategoryGroup.TRANSFER, monthly_budget=None))
    db.commit()


def seed_savings_allocations(db: Session) -> None:
    if db.query(SavingsAllocation).count() > 0:
        return

    for name, target, pattern in SAVINGS_ALLOCATIONS:
        db.add(
            SavingsAllocation(name=name, monthly_target=target, match_pattern=pattern)
        )
    db.commit()


def seed_category_rules(db: Session) -> None:
    if db.query(CategoryRule).count() > 0:
        return

    transfer = db.query(Category).filter_by(name="Transfer").one()
    income = db.query(Category).filter_by(name="Income").one()
    housing = db.query(Category).filter_by(name="Housing").one()

    for pattern in TRANSFER_RULE_PATTERNS:
        db.add(
            CategoryRule(
                pattern=pattern,
                category_id=transfer.id,
                priority=DEFAULT_SEEDED_RULE_PRIORITY,
            )
        )
    for pattern in INCOME_RULE_PATTERNS:
        db.add(
            CategoryRule(
                pattern=pattern,
                category_id=income.id,
                priority=DEFAULT_SEEDED_RULE_PRIORITY,
            )
        )
    for pattern in HOUSING_RULE_PATTERNS:
        db.add(
            CategoryRule(
                pattern=pattern,
                category_id=housing.id,
                priority=DEFAULT_SEEDED_RULE_PRIORITY,
            )
        )
    db.commit()


def seed_all(db: Session) -> None:
    seed_categories(db)
    seed_savings_allocations(db)
    seed_category_rules(db)


if __name__ == "__main__":
    from .db import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_all(db)
    print("Seed complete.")
