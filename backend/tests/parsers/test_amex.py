from datetime import date
from decimal import Decimal

from app.parsers import AmexParser


def test_parses_all_rows(amex_xlsx):
    transactions = AmexParser().parse(amex_xlsx)
    assert len(transactions) == 2


def test_sign_is_flipped_relative_to_native_amex_convention(amex_xlsx):
    transactions = AmexParser().parse(amex_xlsx)
    charge = transactions[0]
    assert charge.date == date(2026, 9, 2)
    # Amex shows charges as positive; normalized form is negative (money out)
    assert charge.amount == Decimal("-5.25")

    payment = transactions[1]
    # Amex shows payments as negative; normalized form is positive (money in)
    assert payment.amount == Decimal("1000.00")


def test_category_hint_is_carried_through(amex_xlsx):
    transactions = AmexParser().parse(amex_xlsx)
    assert transactions[0].source_category_hint == "Restaurant-Bar & Café"
    assert transactions[1].source_category_hint is None


def test_external_id_uses_reference(amex_xlsx):
    transactions = AmexParser().parse(amex_xlsx)
    assert transactions[0].external_id == "amex:REF001"
