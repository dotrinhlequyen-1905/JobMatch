"""Mọi đơn thanh toán bằng VietQR SePay; chế độ demo giả lập webhook SePay qua đúng luồng xác nhận thật."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.core.database import SessionLocal
from app.models import Order, PaymentTransaction, Subscription
from app.services.common import now
from tests.conftest import login, register


def create_order(client, headers, target="CANDIDATE"):
    package = client.get("/api/v1/packages", headers=headers, params={"target": target}).json()[0]
    response = client.post("/api/v1/orders", headers=headers, json={"package_id": package["id"]})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def demo(client, monkeypatch):
    monkeypatch.setattr(settings, "payment_demo_enabled", True)
    monkeypatch.setattr(settings, "enable_dev_tools", False)
    headers = register(client, "premium-demo@t.vn", "CANDIDATE")
    return client, headers, create_order(client, headers)


@pytest.mark.parametrize("demo_enabled", [True, False])
def test_every_order_shows_sepay_vietqr(client, monkeypatch, demo_enabled):
    monkeypatch.setattr(settings, "payment_demo_enabled", demo_enabled)
    for email, role, target in [("qr-cand@t.vn", "CANDIDATE", "CANDIDATE"), ("qr-hr@t.vn", "HR", "HR")]:
        headers = register(client, email, role, "QR company" if role == "HR" else None)
        order = create_order(client, headers, target)
        assert order["qr_url"].startswith("https://qr.sepay.vn/img?")
        assert f"amount={order['amount']}" in order["qr_url"] and f"des={order['order_code']}" in order["qr_url"]
        assert order["bank"]["account"] == settings.sepay_account
        assert order["payment_demo_enabled"] is demo_enabled
        assert client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()["qr_url"] == order["qr_url"]


def test_demo_payment_goes_through_sepay_webhook_and_activates_premium(demo):
    client, headers, order = demo
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["is_premium"] is False

    response = client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers)
    assert response.status_code == 200, response.text
    paid = response.json()
    assert paid["webhook_status"] == "MATCHED"
    assert paid["status"] == "PAID"
    assert paid["paid_at"]
    assert paid["qr_url"] is None
    user = client.get("/api/v1/users/me", headers=headers).json()["user"]
    assert user["is_premium"] is True
    remaining = datetime.fromisoformat(user["premium_until"]) - now()
    assert timedelta(days=order["package"]["duration_days"]) - timedelta(minutes=1) < remaining
    with SessionLocal() as db:
        tx = db.scalar(select(PaymentTransaction).where(PaymentTransaction.order_id == order["id"]))
        assert tx.sepay_tx_id == f"DEMO-{order['id']}-{order['amount']}"
        assert tx.amount == order["amount"]
        assert tx.status == "MATCHED"
        assert order["order_code"] in tx.content
        assert tx.raw_payload["source"] == "demo"


def test_demo_payment_for_hr_package_activates_job_quota(client, monkeypatch):
    monkeypatch.setattr(settings, "payment_demo_enabled", True)
    headers = register(client, "hr-demo@t.vn", "HR", "Demo company")
    order = create_order(client, headers, "HR")
    paid = client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers).json()
    assert paid["status"] == "PAID"
    assert (
        client.get("/api/v1/jobs/quota", headers=headers).json()["subscription"]["remaining"]
        == order["package"]["quota_jobs"]
    )


def test_demo_underpayment_moves_order_to_reconciling(demo):
    client, headers, order = demo
    endpoint = f"/api/v1/orders/{order['id']}/demo-payment"
    underpaid = client.post(endpoint, headers=headers, json={"amount": order["amount"] - 1000}).json()
    assert underpaid["webhook_status"] == "AMOUNT_MISMATCH"
    assert underpaid["status"] == "RECONCILING"
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["is_premium"] is False
    # Đơn đang chờ quản trị viên đối soát thì không thể giả lập thanh toán tiếp.
    assert client.post(endpoint, headers=headers).status_code == 409
    assert client.post(endpoint, headers=headers, json={"amount": 0}).status_code == 422


def test_demo_payment_retry_does_not_extend_premium_twice(demo):
    client, headers, order = demo
    endpoint = f"/api/v1/orders/{order['id']}/demo-payment"
    first = client.post(endpoint, headers=headers).json()
    premium_until = client.get("/api/v1/users/me", headers=headers).json()["user"]["premium_until"]
    second = client.post(endpoint, headers=headers)
    assert second.status_code == 200
    assert second.json()["paid_at"] == first["paid_at"]
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["premium_until"] == premium_until
    with SessionLocal() as db:
        assert (
            db.scalar(select(func.count()).select_from(Subscription).where(Subscription.order_id == order["id"])) == 1
        )
        assert (
            db.scalar(
                select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.order_id == order["id"])
            )
            == 1
        )


def test_demo_renewal_adds_purchased_duration(demo):
    client, headers, order = demo
    assert client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers).status_code == 200
    previous_until = datetime.fromisoformat(
        client.get("/api/v1/users/me", headers=headers).json()["user"]["premium_until"]
    )
    renewal = create_order(client, headers)
    assert renewal["id"] != order["id"]
    assert client.post(f"/api/v1/orders/{renewal['id']}/demo-payment", headers=headers).status_code == 200
    renewed_until = datetime.fromisoformat(
        client.get("/api/v1/users/me", headers=headers).json()["user"]["premium_until"]
    )
    assert renewed_until == previous_until + timedelta(days=renewal["package"]["duration_days"])


def test_demo_payment_requires_order_owner_and_authentication(demo):
    client, headers, order = demo
    endpoint = f"/api/v1/orders/{order['id']}/demo-payment"
    other = register(client, "other-premium@t.vn", "CANDIDATE")
    assert client.post(endpoint).status_code == 401
    assert client.post(endpoint, headers=other).status_code == 404
    assert client.post(endpoint, headers=login(client, "admin@t.vn")).status_code == 404
    assert client.post("/api/v1/orders/999999/demo-payment", headers=headers).status_code == 404
    assert client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()["status"] == "PENDING"


@pytest.mark.parametrize("status", ["CANCELLED", "EXPIRED", "RECONCILING", "REFUNDED", "REFUND_REQUESTED"])
def test_demo_payment_rejects_nonpayable_states(demo, status):
    client, headers, order = demo
    with SessionLocal() as db:
        db.get(Order, order["id"]).status = status
        db.commit()
    response = client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers)
    assert response.status_code == 409
    assert client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()["status"] == status
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["is_premium"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PaymentTransaction)) == 0


@pytest.mark.parametrize("fetch_first", [False, True])
def test_expired_order_is_finalized_without_worker(demo, fetch_first):
    client, headers, order = demo
    with SessionLocal() as db:
        db.get(Order, order["id"]).expires_at = now() - timedelta(seconds=1)
        db.commit()
    if fetch_first:
        expired = client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()
        assert expired["status"] == "EXPIRED"
        assert expired["qr_url"] is None
    assert client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers).status_code == 409
    with SessionLocal() as db:
        assert db.get(Order, order["id"]).status == "EXPIRED"
        assert db.scalar(select(func.count()).select_from(PaymentTransaction)) == 0


def test_demo_payment_can_be_disabled(demo, monkeypatch):
    client, headers, order = demo
    monkeypatch.setattr(settings, "payment_demo_enabled", False)
    detail = client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()
    assert detail["payment_demo_enabled"] is False
    assert detail["qr_url"]
    assert client.post(f"/api/v1/orders/{order['id']}/demo-payment", headers=headers).status_code == 404
    assert client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()["status"] == "PENDING"
