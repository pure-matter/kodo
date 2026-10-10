from decimal import Decimal


def _investment_account(client, name="Fidelity"):
    return client.post(
        "/accounts",
        json={"name": name, "institution": "Fidelity", "type": "investment"},
    ).json()


def test_net_worth_includes_holdings_value(client):
    account = _investment_account(client)
    client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "stock",
            "name": "Apple",
            "symbol": "AAPL",
            "shares": "10",
            "cost_basis": "100.00",
        },
    )

    net_worth = client.get("/net-worth").json()
    # No live price yet -> falls back to shares x cost_basis = 1000.00
    assert Decimal(net_worth["assets"]) == Decimal("1000.00")


def test_net_worth_prefers_holdings_over_a_stale_balance_snapshot(client):
    account = _investment_account(client)
    client.post(
        f"/accounts/{account['id']}/balance-snapshots",
        json={"date": "2026-09-01", "balance": "50000.00"},
    )
    client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "etf",
            "name": "Fidelity low priced",
            "shares": "10",
            "cost_basis": "100.00",
            "manual_value": "1200.00",
        },
    )

    net_worth = client.get("/net-worth").json()
    # Holdings win over the old manual balance snapshot - no double counting
    assert Decimal(net_worth["assets"]) == Decimal("1200.00")


def test_net_worth_includes_uninvested_cash_alongside_holdings(client):
    account = _investment_account(client)
    client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "etf",
            "name": "Fidelity low priced",
            "shares": "10",
            "cost_basis": "100.00",
            "manual_value": "1200.00",
        },
    )
    client.post(
        f"/accounts/{account['id']}/uninvested-cash",
        json={"date": "2026-09-19", "amount": "300.00"},
    )

    net_worth = client.get("/net-worth").json()
    assert Decimal(net_worth["assets"]) == Decimal("1500.00")


def test_net_worth_falls_back_to_balance_snapshot_with_no_holdings(client):
    account = _investment_account(client)
    client.post(
        f"/accounts/{account['id']}/balance-snapshots",
        json={"date": "2026-09-01", "balance": "5000.00"},
    )

    net_worth = client.get("/net-worth").json()
    assert Decimal(net_worth["assets"]) == Decimal("5000.00")


def test_net_worth_includes_unlinked_savings_goal_contributions(client):
    goal = client.post(
        "/savings-goals", json={"name": "Emergency fund", "target_amount": "5000"}
    ).json()
    client.post(f"/savings-goals/{goal['id']}/contributions", json={"date": "2026-09-01", "amount": "800"})

    net_worth = client.get("/net-worth").json()
    assert Decimal(net_worth["assets"]) == Decimal("800.00")


def test_net_worth_excludes_linked_savings_goal_contributions_to_avoid_double_counting(client):
    account = client.post(
        "/accounts", json={"name": "Checking", "institution": "BoA", "type": "checking"}
    ).json()
    client.post(
        f"/accounts/{account['id']}/balance-snapshots",
        json={"date": "2026-09-19", "balance": "3000.00"},
    )
    goal = client.post(
        "/savings-goals",
        json={"name": "Emergency fund", "target_amount": "5000", "linked_account_id": account["id"]},
    ).json()
    client.post(f"/savings-goals/{goal['id']}/contributions", json={"date": "2026-09-01", "amount": "800"})

    net_worth = client.get("/net-worth").json()
    # The 800 is assumed to already be inside the checking account's 3000 -
    # counting it again would overstate assets.
    assert Decimal(net_worth["assets"]) == Decimal("3000.00")
