from datetime import date
from decimal import Decimal

from app.parsers import BoaCreditCardParser


def test_parses_all_rows(boa_credit_card_csv):
    transactions = BoaCreditCardParser().parse(boa_credit_card_csv)
    assert len(transactions) == 3


def test_payment_is_positive_and_charge_is_negative(boa_credit_card_csv):
    transactions = BoaCreditCardParser().parse(boa_credit_card_csv)
    payment = transactions[0]
    assert payment.date == date(2026, 9, 1)
    assert payment.amount == Decimal("1000.00")  # payment in: positive

    charge = transactions[1]
    assert charge.amount == Decimal("-6.50")  # charge: negative


def test_external_id_uses_reference_number(boa_credit_card_csv):
    transactions = BoaCreditCardParser().parse(boa_credit_card_csv)
    assert transactions[0].external_id == "boa_cc:11111111111111111111111"
