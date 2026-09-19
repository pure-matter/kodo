"""Ties a statement parser to the database: parse a file, skip transactions
already imported for that account, categorize the rest, and insert them."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from .categorization import categorize_transaction
from .models import Account, Transaction
from .parsers import AmexParser, BoaCheckingParser, BoaCreditCardParser
from .parsers.base import StatementParser

PARSERS: dict[str, StatementParser] = {
    "boa_checking": BoaCheckingParser(),
    "boa_credit_card": BoaCreditCardParser(),
    "amex": AmexParser(),
}


@dataclass
class ImportSummary:
    total_in_file: int
    imported: int
    skipped_duplicates: int


def import_statement(db: Session, account: Account, file_path: str) -> ImportSummary:
    if account.parser_type is None:
        raise ValueError(
            f"Account {account.name!r} has no parser configured "
            "(it's a manual-entry account) - add transactions by hand instead."
        )
    if account.parser_type not in PARSERS:
        raise ValueError(f"No parser registered for {account.parser_type!r}")

    parser = PARSERS[account.parser_type]
    normalized_transactions = parser.parse(file_path)

    existing_external_ids = {
        row.external_id
        for row in db.query(Transaction.external_id).filter_by(account_id=account.id)
    }

    imported = 0
    skipped = 0
    for txn in normalized_transactions:
        if txn.external_id in existing_external_ids:
            skipped += 1
            continue

        category_id = categorize_transaction(db, txn.description, txn.source_category_hint)
        db.add(
            Transaction(
                account_id=account.id,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                external_id=txn.external_id,
                category_id=category_id,
                source_category_hint=txn.source_category_hint,
            )
        )
        imported += 1

    db.commit()
    return ImportSummary(
        total_in_file=len(normalized_transactions),
        imported=imported,
        skipped_duplicates=skipped,
    )
