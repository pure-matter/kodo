def _create_account(client, name="Fidelity"):
    return client.post(
        "/accounts",
        json={"name": name, "institution": "Fidelity", "type": "investment"},
    ).json()


def test_create_and_list_holdings(client):
    account = _create_account(client)
    response = client.post(
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
    assert response.status_code == 201
    holding = response.json()
    assert holding["current_value"] == "1000.00"

    listed = client.get("/holdings").json()
    assert len(listed) == 1


def test_update_holding(client):
    account = _create_account(client)
    holding = client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "real_estate",
            "name": "Land",
            "cost_basis": "50000",
            "manual_value": "50000",
        },
    ).json()

    response = client.patch(f"/holdings/{holding['id']}", json={"manual_value": "60000"})
    assert response.status_code == 200
    assert response.json()["current_value"] == "60000.00"


def test_delete_missing_holding_is_404(client):
    response = client.delete("/holdings/999")
    assert response.status_code == 404


def test_refresh_price_without_api_key_returns_502(client, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    account = _create_account(client)
    holding = client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "stock",
            "name": "Apple",
            "symbol": "AAPL",
            "shares": "10",
            "cost_basis": "100.00",
        },
    ).json()

    response = client.post(f"/holdings/{holding['id']}/refresh-price")
    assert response.status_code == 502


def test_refresh_price_without_symbol_returns_400(client):
    account = _create_account(client)
    holding = client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "real_estate",
            "name": "Land",
            "cost_basis": "50000",
            "manual_value": "50000",
        },
    ).json()

    response = client.post(f"/holdings/{holding['id']}/refresh-price")
    assert response.status_code == 400


def test_portfolio_breakdown_by_type_and_account(client):
    account = _create_account(client)
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
    client.post(
        "/holdings",
        json={
            "account_id": account["id"],
            "investment_type": "real_estate",
            "name": "Land",
            "cost_basis": "1000",
            "manual_value": "1000",
        },
    )

    summary = client.get("/looking-ahead/summary").json()
    assert summary["total_portfolio_value"] == "2000.00"
    by_type_labels = {s["label"] for s in summary["by_type"]}
    assert by_type_labels == {"stock", "real_estate"}
    land_slice = next(s for s in summary["by_type"] if s["label"] == "real_estate")
    assert land_slice["percent_of_total"] == "50.00"


def test_create_goal_and_log_contributions(client):
    response = client.post(
        "/savings-goals",
        json={"name": "Emergency fund", "target_amount": "5000", "target_date": "2027-01-01"},
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["contributed"] == "0"
    assert goal["achieved_at"] is None

    client.post(f"/savings-goals/{goal['id']}/contributions", json={"date": "2026-01-01", "amount": "500"})
    updated = client.get("/savings-goals").json()[0]
    assert updated["contributed"] == "500.00"


def test_goal_is_marked_achieved_once_target_is_met(client):
    goal = client.post(
        "/savings-goals", json={"name": "New laptop", "target_amount": "1000"}
    ).json()

    client.post(f"/savings-goals/{goal['id']}/contributions", json={"date": "2026-01-01", "amount": "1000"})

    summary = client.get("/looking-ahead/summary").json()
    assert len(summary["achieved_goals"]) == 1
    assert len(summary["goals"]) == 0


def test_create_and_delete_recurring_investment(client):
    goal = client.post("/savings-goals", json={"name": "House", "target_amount": "50000"}).json()
    response = client.post(
        "/recurring-investments",
        json={"name": "Roth IRA", "amount": "200", "frequency": "monthly", "goal_id": goal["id"]},
    )
    assert response.status_code == 201
    recurring = response.json()

    assert client.delete(f"/recurring-investments/{recurring['id']}").status_code == 204
    assert client.get("/recurring-investments").json() == []


def test_log_and_relog_uninvested_cash_upserts(client):
    account = _create_account(client)
    client.post(
        f"/accounts/{account['id']}/uninvested-cash",
        json={"date": "2026-01-01", "amount": "100"},
    )
    response = client.post(
        f"/accounts/{account['id']}/uninvested-cash",
        json={"date": "2026-01-01", "amount": "150"},
    )
    assert response.status_code == 200
    entries = client.get(f"/accounts/{account['id']}/uninvested-cash").json()
    assert len(entries) == 1
    assert entries[0]["amount"] == "150.00"
