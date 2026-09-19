from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import openpyxl

from .base import NormalizedTransaction

_HEADER_MARKER = "Date"


class AmexParser:
    """Parses American Express 'Transaction Details' XLSX exports.

    Amex's sign convention is the opposite of BoA's: charges are positive
    and payments/credits are negative. We flip the sign here so every
    parser in this package agrees on one convention: negative = money out,
    positive = money in. Amex also tags each row with its own category
    (e.g. "Restaurant-Bar & Café"), which we carry through as a hint for
    seeding category rules.
    """

    SHEET_NAME = "Transaction Details"

    def parse(self, file_path: str) -> list[NormalizedTransaction]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb[self.SHEET_NAME]
        rows = list(ws.iter_rows(values_only=True))

        header_idx = next(i for i, row in enumerate(rows) if row[0] == _HEADER_MARKER)
        col = {name: idx for idx, name in enumerate(rows[header_idx])}

        transactions = []
        for row in rows[header_idx + 1 :]:
            if not row[col["Date"]]:
                continue
            amex_amount = Decimal(str(row[col["Amount"]]))
            transactions.append(
                NormalizedTransaction(
                    date=datetime.strptime(row[col["Date"]], "%m/%d/%Y").date(),
                    description=str(row[col["Description"]]).strip(),
                    amount=-amex_amount,
                    external_id=f"amex:{row[col['Reference']]}",
                    source_category_hint=row[col["Category"]] or None,
                )
            )
        return transactions
