from app.config import settings
from tests.conftest import register


def order(client, headers):
    package = client.get("/api/v1/packages", headers=headers, params={"target": "HR"}).json()[0]
    response = client.post("/api/v1/orders", headers=headers, json={"package_id": package["id"]})
    assert response.status_code == 200
    return response.json()


def test_disabled_simulation_is_advertised_and_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "enable_dev_tools", False)
    headers = register(client, "simulation@t.vn", "HR", "Test company")
    created = order(client, headers)
    assert created["payment_simulation_enabled"] is False
    fetched = client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()
    assert fetched["payment_simulation_enabled"] is False
    response = client.post("/api/v1/dev/simulate-payment", headers=headers, json={"order_id": created["id"]})
    assert response.status_code == 404
    assert client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()["status"] == "PENDING"


def test_enabled_simulation_uses_webhook_checks_and_activation(client, monkeypatch):
    monkeypatch.setattr(settings, "enable_dev_tools", True)
    headers = register(client, "simulation@t.vn", "HR", "Test company")
    other = register(client, "other@t.vn", "HR", "Other company")
    created = order(client, headers)
    assert created["payment_simulation_enabled"] is True
    fetched = client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()
    assert fetched["payment_simulation_enabled"] is True
    endpoint = "/api/v1/dev/simulate-payment"
    assert client.post(endpoint, headers=other, json={"order_id": created["id"]}).status_code == 404
    underpaid = client.post(endpoint, headers=headers, json={"order_id": created["id"], "amount": created["amount"] - 1000})
    assert underpaid.status_code == 200
    assert underpaid.json()["result"]["status"] == "AMOUNT_MISMATCH"
    assert client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()["status"] == "RECONCILING"
    paid = client.post(endpoint, headers=headers, json={"order_id": created["id"], "tx_id": "SIM-TEST"})
    assert paid.status_code == 200
    assert paid.json()["result"]["status"] == "MATCHED"
    assert client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()["status"] == "PAID"
    duplicate = client.post(endpoint, headers=headers, json={"order_id": created["id"], "tx_id": "SIM-TEST"})
    assert duplicate.json()["result"]["status"] == "DUPLICATE"
    quota = client.get("/api/v1/jobs/quota", headers=headers).json()
    assert quota["subscription"]["remaining"] == 5
