from app.categorization import categorize_transaction, learn_rule, match_rule
from app.models import Category, CategoryGroup, CategoryRule
from app.seed import seed_all


def _category_id(db, name):
    return db.query(Category).filter_by(name=name).one().id


def test_seeded_rules_flag_real_transfer_patterns_as_transfer(db_session):
    seed_all(db_session)
    transfer_id = _category_id(db_session, "Transfer")

    real_descriptions = [
        "AMERICAN EXPRESS DES:ACH PMT ID:M6948 INDN:ISATOU SAHO CO ID:1133133497 WEB",
        "CITI CARD ONLINE DES:PAYMENT ID:432121495942395 INDN:ISATOU SAHO CO ID:CITICTP WEB",
        "MOBILE PAYMENT - THANK YOU",
        "AUTOPAY PAYMENT - THANK YOU",
        "ONLINE/MOBILE RECURRING FROM CHK 0171",
        "Online Scheduled Payment to ACCT# 8600 Confirmation# 2162883952",
        "ROBINHOOD DES:DEBITS ID:452664436 INDN:Isatou Saho CO ID:5326394001 WEB",
        "FID BKG SVC LLC DES:MONEYLINE ID:603832431 FPXD2 INDN:ISATOU SAHO CO ID:0368004600 PPD",
    ]
    for description in real_descriptions:
        assert (
            categorize_transaction(db_session, description, None) == transfer_id
        ), description


def test_seeded_rule_flags_apple_payroll_as_income(db_session):
    seed_all(db_session)
    income_id = _category_id(db_session, "Income")

    assert (
        categorize_transaction(
            db_session,
            "APPLE INC. DES:PAYROLL ID:682899 INDN:Isatou Saho CO ID:1942404110 PPD",
            None,
        )
        == income_id
    )


def test_seeded_rule_flags_mortgage_as_housing(db_session):
    seed_all(db_session)
    housing_id = _category_id(db_session, "Housing")

    assert (
        categorize_transaction(
            db_session,
            "FREEDOM DES:MTG PYMTS ID:0169313160 INDN:ISATOU SAHO CO ID:1223039688 WEB",
            None,
        )
        == housing_id
    )


def test_unmatched_zelle_to_a_person_is_uncategorized(db_session):
    # Zelle recipients vary, so there's no generic rule for these - they
    # should stay uncategorized until the user assigns one manually.
    seed_all(db_session)
    assert categorize_transaction(db_session, "Zelle payment to mom Conf# q2cutlqi5", None) is None


def test_amex_hint_is_used_when_no_rule_matches(db_session):
    seed_all(db_session)
    groceries_id = _category_id(db_session, "Groceries")

    result = categorize_transaction(
        db_session,
        "AplPay TRADER JOE S AUSTIN TX",
        "Merchandise & Supplies-Groceries",
    )
    assert result == groceries_id


def test_explicit_rule_takes_precedence_over_amex_hint(db_session):
    seed_all(db_session)
    coffee_id = _category_id(db_session, "Coffee/Dessert")
    # Amex's export runs the merchant name straight into the city with no
    # space, truncating "COFFEE" to "COFFE" here - the learned pattern has
    # to match the real truncated text, not the "clean" merchant name.
    learn_rule(db_session, pattern="INSTILL COFFE", category_id=coffee_id)

    # Amex tags this merchant as "Restaurant-Bar & Café" (-> Eating Out by
    # default), but the learned rule for this specific merchant should win.
    result = categorize_transaction(
        db_session,
        "AplPay INSTILL COFFECedar Park          TX",
        "Restaurant-Bar & Café",
    )
    assert result == coffee_id


def test_learn_rule_is_idempotent(db_session):
    seed_all(db_session)
    family_id = _category_id(db_session, "Family")

    learn_rule(db_session, pattern="Zelle payment to mom", category_id=family_id)
    learn_rule(db_session, pattern="Zelle payment to mom", category_id=family_id)

    rules = (
        db_session.query(CategoryRule)
        .filter_by(pattern="Zelle payment to mom", category_id=family_id)
        .all()
    )
    assert len(rules) == 1


def test_match_rule_respects_priority_order():
    rules = [
        CategoryRule(pattern="COFFEE", category_id=1, priority=100),
        CategoryRule(pattern="INSTILL COFFEE", category_id=2, priority=10),
    ]
    # Both patterns match; the lower-priority-number (more specific) rule wins
    assert match_rule("AplPay INSTILL COFFEE Cedar Park TX", rules) == 2
