from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal

from .base import NormalizedTransaction


class BoaCreditCardParser:
    """Parses Bank of America credit card CSV exports.

    Single clean header row, no preamble. Same sign convention as the
    checking export: charges are negative, payments/credits are positive.
    Each row carries a Reference Number, so we use that directly for dedup
    instead of hashing fields.
    """

    def parse(self, file_path: str) -> list[NormalizedTransaction]:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            transactions = [
                NormalizedTransaction(
                    date=datetime.strptime(row["Posted Date"], "%m/%d/%Y").date(),
                    description=row["Payee"].strip(),
                    amount=Decimal(row["Amount"]),
                    external_id=f"boa_cc:{row['Reference Number']}",
                )
                for row in reader
            ]
        return transactions
