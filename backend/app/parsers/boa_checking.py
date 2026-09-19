from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .base import NormalizedTransaction, make_external_id

_HEADER_MARKER = ("Date", "Description", "Amount", "Running Bal.")


class BoaCheckingParser:
    """Parses Bank of America checking/savings account CSV exports.

    BoA exports these with a summary preamble (beginning/ending balance,
    totals) before the real transaction table, and repeats the beginning
    balance as a row with no Amount, so we scan for the header row and
    skip balance-only rows rather than assuming a fixed offset.
    """

    def parse(self, file_path: str) -> list[NormalizedTransaction]:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))

        header_idx = next(
            i for i, row in enumerate(rows) if tuple(row[:4]) == _HEADER_MARKER
        )

        transactions = []
        for row in rows[header_idx + 1 :]:
            if len(row) < 4 or not row[0]:
                continue
            date_str, description, amount_str, running_bal_str = row[:4]
            if not amount_str.strip():
                continue  # "Beginning balance as of ..." row has no Amount
            transactions.append(
                NormalizedTransaction(
                    date=datetime.strptime(date_str, "%m/%d/%Y").date(),
                    description=description,
                    amount=_parse_amount(amount_str),
                    external_id=make_external_id(
                        "boa_checking",
                        date_str,
                        description,
                        amount_str,
                        running_bal_str,
                    ),
                )
            )
        return transactions


def _parse_amount(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse amount: {value!r}") from exc
