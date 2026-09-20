from datetime import date
from decimal import Decimal

from app.models import Category, MonthlySpendSummary, Transaction
from app.reporting import archive_month, monthly_history
from app.seed import seed_all


def _category_id(db, name):
    return db.query(Category).filter_by(name=name).one().id


def _add_transaction(db, account_id, day, amount, category_id, external_id):
    db.add(
        Transaction(
            account_id=account_id,
            date=day,
            description="test",
            amount=amount,
            category_id=category_id,
            external_id=external_id,
        )
    )


def test_archive_month_snapshots_totals_then_deletes_transactions(db_session):
    from app.models import Account, AccountType

    seed_all(db_session)
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    groceries_id = _category_id(db_session, "Groceries")
    _add_transaction(db_session, account.id, date(2026, 9, 3), Decimal("-150"), groceries_id, "a")
    _add_transaction(db_session, account.id, date(2026, 9, 10), Decimal("-50"), groceries_id, "b")
    _add_transaction(db_session, account.id, date(2026, 8, 1), Decimal("-30"), groceries_id, "c")
    db_session.commit()

    archive_month(db_session, 2026, 9)

    summary = (
        db_session.query(MonthlySpendSummary)
        .filter_by(category_id=groceries_id, year=2026, month=9)
        .one()
    )
    assert summary.spent == Decimal("200.00")

    remaining = db_session.query(Transaction).all()
    assert len(remaining) == 1  # only the August transaction survives
    assert remaining[0].external_id == "c"


def test_archiving_the_same_month_twice_updates_rather_than_duplicates(db_session):
    from app.models import Account, AccountType

    seed_all(db_session)
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    groceries_id = _category_id(db_session, "Groceries")
    _add_transaction(db_session, account.id, date(2026, 9, 3), Decimal("-100"), groceries_id, "a")
    db_session.commit()

    archive_month(db_session, 2026, 9)

    _add_transaction(db_session, account.id, date(2026, 9, 15), Decimal("-25"), groceries_id, "b")
    db_session.commit()
    archive_month(db_session, 2026, 9)

    summaries = (
        db_session.query(MonthlySpendSummary).filter_by(category_id=groceries_id, year=2026, month=9).all()
    )
    assert len(summaries) == 1
    assert summaries[0].spent == Decimal("25.00")


def test_monthly_history_prefers_archived_summary_over_live_zero(db_session):
    from app.models import Account, AccountType

    seed_all(db_session)
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    groceries_id = _category_id(db_session, "Groceries")
    today = date.today()
    _add_transaction(db_session, account.id, today.replace(day=1), Decimal("-75"), groceries_id, "x")
    db_session.commit()

    archive_month(db_session, today.year, today.month)  # deletes the transaction

    history = monthly_history(db_session, months=1)
    groceries_row = next(r for r in history if r["category_id"] == groceries_id)
    assert groceries_row["spent"] == Decimal("75.00")  # from the archive, not a live 0


def test_monthly_history_uses_live_data_for_unarchived_months(db_session):
    from app.models import Account, AccountType

    seed_all(db_session)
    account = Account(name="Checking", institution="BoA", type=AccountType.CHECKING)
    db_session.add(account)
    db_session.flush()

    groceries_id = _category_id(db_session, "Groceries")
    today = date.today()
    _add_transaction(db_session, account.id, today.replace(day=1), Decimal("-40"), groceries_id, "y")
    db_session.commit()

    history = monthly_history(db_session, months=1)
    groceries_row = next(r for r in history if r["category_id"] == groceries_id)
    assert groceries_row["spent"] == Decimal("40.00")
