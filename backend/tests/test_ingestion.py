from decimal import Decimal

import pytest

from app.ingestion import import_statement
from app.models import Account, AccountType, Category, Transaction
from app.seed import seed_all

FIXTURES_DIR_CHECKING = "tests/parsers/fixtures/boa_checking_sample.csv"
FIXTURES_DIR_CC = "tests/parsers/fixtures/boa_credit_card_sample.csv"


@pytest.fixture
def checking_account(db_session):
    seed_all(db_session)
    account = Account(
        name="Checking",
        institution="Bank of America",
        type=AccountType.CHECKING,
        parser_type="boa_checking",
    )
    db_session.add(account)
    db_session.commit()
    return account


def test_import_creates_transactions(db_session, checking_account):
    summary = import_statement(db_session, checking_account, FIXTURES_DIR_CHECKING)

    assert summary.total_in_file == 4
    assert summary.imported == 4
    assert summary.skipped_duplicates == 0

    transactions = db_session.query(Transaction).filter_by(account_id=checking_account.id).all()
    assert len(transactions) == 4


def test_reimporting_same_file_is_a_no_op(db_session, checking_account):
    import_statement(db_session, checking_account, FIXTURES_DIR_CHECKING)
    summary = import_statement(db_session, checking_account, FIXTURES_DIR_CHECKING)

    assert summary.imported == 0
    assert summary.skipped_duplicates == 4
    assert db_session.query(Transaction).filter_by(account_id=checking_account.id).count() == 4


def test_import_categorizes_known_patterns(db_session, checking_account):
    import_statement(db_session, checking_account, FIXTURES_DIR_CHECKING)

    payroll = (
        db_session.query(Transaction)
        .filter(Transaction.description.contains("APPLE INC"))
        .one()
    )
    transfer = (
        db_session.query(Transaction)
        .filter(Transaction.description.contains("AMERICAN EXPRESS"))
        .one()
    )
    grocery = (
        db_session.query(Transaction)
        .filter(Transaction.description.contains("SAMPLE GROCERY STORE"))
        .first()
    )

    income_id = db_session.query(Category).filter_by(name="Income").one().id
    transfer_id = db_session.query(Category).filter_by(name="Transfer").one().id

    assert payroll.category_id == income_id
    assert transfer.category_id == transfer_id
    # No rule/hint matches a generic grocery store description -> uncategorized
    assert grocery.category_id is None


def test_import_into_manual_account_raises(db_session):
    seed_all(db_session)
    manual_account = Account(
        name="GTBank", institution="GTBank", type=AccountType.CHECKING, parser_type=None
    )
    db_session.add(manual_account)
    db_session.commit()

    with pytest.raises(ValueError, match="manual-entry account"):
        import_statement(db_session, manual_account, FIXTURES_DIR_CHECKING)


def test_import_across_two_accounts_does_not_share_dedup_state(db_session):
    seed_all(db_session)
    checking = Account(
        name="Checking",
        institution="BoA",
        type=AccountType.CHECKING,
        parser_type="boa_checking",
    )
    travel_card = Account(
        name="Travel Card",
        institution="BoA",
        type=AccountType.CREDIT,
        parser_type="boa_credit_card",
    )
    db_session.add_all([checking, travel_card])
    db_session.commit()

    checking_summary = import_statement(db_session, checking, FIXTURES_DIR_CHECKING)
    cc_summary = import_statement(db_session, travel_card, FIXTURES_DIR_CC)

    assert checking_summary.imported == 4
    assert cc_summary.imported == 3
