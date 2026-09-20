from decimal import Decimal


def _category_id_by_name(client, name):
    categories = client.get("/categories").json()
    return next(c["id"] for c in categories if c["name"] == name)


def test_create_and_list_accounts(client):
    response = client.post(
        "/accounts",
        json={
            "name": "Checking",
            "institution": "Bank of America",
            "type": "checking",
            "parser_type": "boa_checking",
        },
    )
    assert response.status_code == 201
    account = response.json()
    assert account["name"] == "Checking"

    response = client.get("/accounts")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_missing_account_is_404(client):
    response = client.get("/accounts/999")
    assert response.status_code == 404


def test_import_statement_via_api(client):
    account = client.post(
        "/accounts",
        json={
            "name": "Checking",
            "institution": "Bank of America",
            "type": "checking",
            "parser_type": "boa_checking",
        },
    ).json()

    with open("tests/parsers/fixtures/boa_checking_sample.csv", "rb") as f:
        response = client.post(
            f"/accounts/{account['id']}/import",
            files={"file": ("statement.csv", f, "text/csv")},
        )

    assert response.status_code == 200
    summary = response.json()
    assert summary["imported"] == 4
    assert summary["skipped_duplicates"] == 0

    transactions = client.get("/transactions", params={"account_id": account["id"]}).json()
    assert len(transactions) == 4


def test_import_into_manual_account_returns_400(client):
    account = client.post(
        "/accounts",
        json={"name": "GTBank", "institution": "GTBank", "type": "checking"},
    ).json()

    with open("tests/parsers/fixtures/boa_checking_sample.csv", "rb") as f:
        response = client.post(
            f"/accounts/{account['id']}/import",
            files={"file": ("statement.csv", f, "text/csv")},
        )
    assert response.status_code == 400


def test_create_manual_transaction(client):
    account = client.post(
        "/accounts",
        json={"name": "GTBank", "institution": "GTBank", "type": "checking"},
    ).json()

    response = client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-09-01",
            "description": "School fee",
            "amount": "-100.00",
        },
    )
    assert response.status_code == 201
    assert response.json()["category_id"] is None


def test_recategorize_transaction_and_learn_rule(client):
    account = client.post(
        "/accounts",
        json={"name": "GTBank", "institution": "GTBank", "type": "checking"},
    ).json()
    transaction = client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-09-01",
            "description": "SCHOOL FEE PAYMENT REF001",
            "amount": "-100.00",
        },
    ).json()

    education_id = _category_id_by_name(client, "Education")
    response = client.patch(
        f"/transactions/{transaction['id']}",
        json={
            "category_id": education_id,
            "create_rule": True,
            "pattern": "SCHOOL FEE PAYMENT",
        },
    )
    assert response.status_code == 200
    assert response.json()["category_id"] == education_id

    rules = client.get("/category-rules").json()
    assert any(r["pattern"] == "SCHOOL FEE PAYMENT" for r in rules)

    # A second, similar manual transaction should now auto-categorize on
    # its own the next time a real import runs the same rule engine - here
    # we just confirm the rule persisted and is queryable via the API.


def test_recategorize_without_pattern_when_create_rule_true_is_400(client):
    account = client.post(
        "/accounts",
        json={"name": "GTBank", "institution": "GTBank", "type": "checking"},
    ).json()
    transaction = client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-09-01",
            "description": "Something",
            "amount": "-10.00",
        },
    ).json()
    misc_id = _category_id_by_name(client, "Misc")

    response = client.patch(
        f"/transactions/{transaction['id']}",
        json={"category_id": misc_id, "create_rule": True},
    )
    assert response.status_code == 400


def test_budget_summary_reflects_spend(client):
    account = client.post(
        "/accounts",
        json={
            "name": "Checking",
            "institution": "Bank of America",
            "type": "checking",
            "parser_type": "boa_checking",
        },
    ).json()
    with open("tests/parsers/fixtures/boa_checking_sample.csv", "rb") as f:
        client.post(
            f"/accounts/{account['id']}/import",
            files={"file": ("statement.csv", f, "text/csv")},
        )

    summary = client.get("/reports/budget-summary", params={"year": 2026, "month": 9}).json()
    groceries = next(item for item in summary if item["category_name"] == "Groceries")
    # Nothing in the fixture auto-categorizes as Groceries (no rule/hint matches)
    assert Decimal(groceries["spent"]) == Decimal("0")

    # Recategorize the two uncategorized grocery-store transactions by hand,
    # then confirm the budget summary picks up the real spend total.
    groceries_id = groceries["category_id"]
    grocery_transactions = [
        t
        for t in client.get("/transactions", params={"account_id": account["id"]}).json()
        if "SAMPLE GROCERY STORE" in t["description"]
    ]
    assert len(grocery_transactions) == 2
    for t in grocery_transactions:
        client.patch(f"/transactions/{t['id']}", json={"category_id": groceries_id})

    summary = client.get("/reports/budget-summary", params={"year": 2026, "month": 9}).json()
    groceries = next(item for item in summary if item["category_name"] == "Groceries")
    assert Decimal(groceries["spent"]) == Decimal("300.00")  # two $150 charges


def test_savings_progress_tracks_matched_transfers(client):
    account = client.post(
        "/accounts",
        json={
            "name": "Checking",
            "institution": "Bank of America",
            "type": "checking",
            "parser_type": "boa_checking",
        },
    ).json()
    with open("tests/parsers/fixtures/boa_checking_sample.csv", "rb") as f:
        client.post(
            f"/accounts/{account['id']}/import",
            files={"file": ("statement.csv", f, "text/csv")},
        )

    progress = client.get("/savings-allocations/progress", params={"year": 2026, "month": 9}).json()
    # The fixture has no Robinhood/FID transactions, so contributed stays 0
    for item in progress:
        assert Decimal(item["contributed"]) == Decimal("0")


def test_net_worth_from_balance_snapshots(client):
    checking = client.post(
        "/accounts",
        json={"name": "Checking", "institution": "BoA", "type": "checking"},
    ).json()
    credit_card = client.post(
        "/accounts",
        json={"name": "Amex", "institution": "Amex", "type": "credit"},
    ).json()

    client.post(
        f"/accounts/{checking['id']}/balance-snapshots",
        json={"date": "2026-09-19", "balance": "2000.00"},
    )
    client.post(
        f"/accounts/{credit_card['id']}/balance-snapshots",
        json={"date": "2026-09-19", "balance": "500.00"},
    )

    net_worth = client.get("/net-worth").json()
    assert Decimal(net_worth["assets"]) == Decimal("2000.00")
    assert Decimal(net_worth["liabilities"]) == Decimal("500.00")
    assert Decimal(net_worth["net_worth"]) == Decimal("1500.00")


def test_logging_a_second_balance_same_day_updates_instead_of_erroring(client):
    account = client.post(
        "/accounts",
        json={"name": "Fidelity", "institution": "Fidelity", "type": "investment"},
    ).json()

    first = client.post(
        f"/accounts/{account['id']}/balance-snapshots",
        json={"date": "2026-09-19", "balance": "1000.00"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/accounts/{account['id']}/balance-snapshots",
        json={"date": "2026-09-19", "balance": "1050.00"},
    )
    assert second.status_code == 200
    assert Decimal(second.json()["balance"]) == Decimal("1050.00")

    net_worth = client.get("/net-worth").json()
    # Only the updated value counts - no duplicate row inflating assets
    assert Decimal(net_worth["assets"]) == Decimal("1050.00")


def test_update_account(client):
    account = client.post(
        "/accounts",
        json={"name": "Checking", "institution": "BoA", "type": "checking"},
    ).json()

    response = client.patch(f"/accounts/{account['id']}", json={"name": "Joint Checking"})
    assert response.status_code == 200
    assert response.json()["name"] == "Joint Checking"
    assert response.json()["institution"] == "BoA"  # untouched fields survive


def test_update_category_budget(client):
    groceries_id = _category_id_by_name(client, "Groceries")
    response = client.patch(f"/categories/{groceries_id}", json={"monthly_budget": "500"})
    assert response.status_code == 200
    assert Decimal(response.json()["monthly_budget"]) == Decimal("500")


def test_rename_category(client):
    groceries_id = _category_id_by_name(client, "Groceries")
    response = client.patch(f"/categories/{groceries_id}", json={"name": "Food & Groceries"})
    assert response.status_code == 200
    assert response.json()["name"] == "Food & Groceries"


def test_create_and_delete_unused_category(client):
    created = client.post(
        "/categories", json={"name": "Pets", "group": "wants", "monthly_budget": "50"}
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    response = client.delete(f"/categories/{category_id}")
    assert response.status_code == 204
    assert category_id not in [c["id"] for c in client.get("/categories").json()]


def test_cannot_delete_category_with_transactions(client):
    account = client.post(
        "/accounts",
        json={"name": "GTBank", "institution": "GTBank", "type": "checking"},
    ).json()
    groceries_id = _category_id_by_name(client, "Groceries")
    client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-09-01",
            "description": "Store run",
            "amount": "-40.00",
            "category_id": groceries_id,
        },
    )

    response = client.delete(f"/categories/{groceries_id}")
    assert response.status_code == 400


def test_deleting_category_cascades_its_rules(client):
    created = client.post(
        "/categories", json={"name": "Pets", "group": "wants", "monthly_budget": None}
    ).json()
    client.post("/category-rules", json={"pattern": "PETCO", "category_id": created["id"]})

    client.delete(f"/categories/{created['id']}")

    rules = client.get("/category-rules").json()
    assert not any(r["pattern"] == "PETCO" for r in rules)


def test_update_and_delete_category_rule(client):
    groceries_id = _category_id_by_name(client, "Groceries")
    rule = client.post(
        "/category-rules", json={"pattern": "TRADER JOE", "category_id": groceries_id}
    ).json()

    updated = client.patch(f"/category-rules/{rule['id']}", json={"priority": 5})
    assert updated.status_code == 200
    assert updated.json()["priority"] == 5

    deleted = client.delete(f"/category-rules/{rule['id']}")
    assert deleted.status_code == 204
    assert rule["id"] not in [r["id"] for r in client.get("/category-rules").json()]


def test_archive_month_via_api_then_transactions_are_gone(client):
    account = client.post(
        "/accounts",
        json={
            "name": "Checking",
            "institution": "Bank of America",
            "type": "checking",
            "parser_type": "boa_checking",
        },
    ).json()
    with open("tests/parsers/fixtures/boa_checking_sample.csv", "rb") as f:
        client.post(
            f"/accounts/{account['id']}/import",
            files={"file": ("statement.csv", f, "text/csv")},
        )

    groceries_id = _category_id_by_name(client, "Groceries")
    grocery_transactions = [
        t
        for t in client.get("/transactions", params={"account_id": account["id"]}).json()
        if "SAMPLE GROCERY STORE" in t["description"]
    ]
    for t in grocery_transactions:
        client.patch(f"/transactions/{t['id']}", json={"category_id": groceries_id})

    response = client.post("/reports/archive-month", json={"year": 2026, "month": 9})
    assert response.status_code == 200
    archived_groceries = next(r for r in response.json() if r["category_name"] == "Groceries")
    assert Decimal(archived_groceries["spent"]) == Decimal("300.00")

    remaining = client.get("/transactions", params={"account_id": account["id"]}).json()
    assert remaining == []  # raw transactions are gone

    history = client.get("/reports/monthly-history", params={"months": 1}).json()
    groceries_row = next(r for r in history if r["category_name"] == "Groceries")
    assert Decimal(groceries_row["spent"]) == Decimal("300.00")  # total survives the deletion
