from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def boa_checking_csv() -> str:
    return str(FIXTURES_DIR / "boa_checking_sample.csv")


@pytest.fixture
def boa_credit_card_csv() -> str:
    return str(FIXTURES_DIR / "boa_credit_card_sample.csv")


@pytest.fixture
def amex_xlsx(tmp_path) -> str:
    """Builds a synthetic Amex 'Transaction Details' workbook matching the
    real export's layout: a preamble block, then the header row, then rows.
    Generated at test time so no binary fixture needs to live in the repo.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Transaction Details"
    ws.append(["Transaction Details", "American Express Gold Card / Sample Period"])
    ws.append(["Prepared for", ""])
    ws.append(["JANE DOE", ""])
    ws.append(["Account Number", ""])
    ws.append(["XXXX-XXXXXX-01000", ""])
    ws.append([""])
    ws.append(
        [
            "Date",
            "Description",
            "Amount",
            "Extended Details",
            "Appears On Your Statement As",
            "Address",
            "City/State",
            "Zip Code",
            "Country",
            "Reference",
            "Category",
        ]
    )
    ws.append(
        [
            "09/02/2026",
            "SAMPLE COFFEE SHOP AUSTIN TX",
            5.25,
            "",
            "",
            "",
            "",
            "",
            "UNITED STATES",
            "REF001",
            "Restaurant-Bar & Café",
        ]
    )
    ws.append(
        [
            "09/03/2026",
            "MOBILE PAYMENT - THANK YOU",
            -1000.00,
            "",
            "",
            "",
            "",
            "",
            "UNITED STATES",
            "REF002",
            "",
        ]
    )

    path = tmp_path / "amex_sample.xlsx"
    wb.save(path)
    return str(path)
