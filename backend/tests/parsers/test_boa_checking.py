from datetime import date
from decimal import Decimal

from app.parsers import BoaCheckingParser


def test_skips_preamble_and_beginning_balance_row(boa_checking_csv):
    transactions = BoaCheckingParser().parse(boa_checking_csv)
    assert len(transactions) == 4  # 5 data rows minus the beginning-balance row


def test_parses_thousands_separator_and_sign(boa_checking_csv):
    transactions = BoaCheckingParser().parse(boa_checking_csv)
    payroll = transactions[0]
    assert payroll.date == date(2026, 9, 2)
    assert payroll.amount == Decimal("2500.00")  # income: positive

    purchase = transactions[1]
    assert purchase.amount == Decimal("-150.00")  # expense: negative


def test_dedup_ids_are_unique_even_for_identical_amount_rows(boa_checking_csv):
    transactions = BoaCheckingParser().parse(boa_checking_csv)
    # Two "SAMPLE GROCERY STORE" rows share date-independent fields but
    # differ in running balance, which the hash must pick up on.
    grocery_ids = {t.external_id for t in transactions if "GROCERY" in t.description}
    assert len(grocery_ids) == 2
