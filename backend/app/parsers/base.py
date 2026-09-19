from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class NormalizedTransaction:
    """A transaction normalized to a common shape across bank sources.

    amount sign convention (same across every parser): negative means money
    left the account (an expense or a transfer out), positive means money
    came into the account (income, a refund, or a transfer/payment in).
    Whether a given transaction counts as real spend/income vs. an internal
    transfer between the user's own accounts is a categorization concern,
    not a parsing concern.
    """

    date: date
    description: str
    amount: Decimal
    external_id: str
    source_category_hint: str | None = None


class StatementParser(Protocol):
    def parse(self, file_path: str) -> list[NormalizedTransaction]:
        ...


def make_external_id(*parts: str) -> str:
    """Stable dedup id for sources with no natural unique reference number."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:24]
