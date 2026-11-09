"""Real password recovery sends links by SMTP without exposing them in API responses."""

import hashlib
import re
import smtplib
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.core import mailer
from app.core.database import SessionLocal
from app.models import AuthToken, User
from app.services import auth as auth_service
from app.services.common import now
from app.tasks.notification_tasks import send_email
from tests.conftest import register

API = "/api/v1/auth"
EMAIL = "resetflow@t.vn"


@pytest.fixture()
def recovery(client, monkeypatch):
    # Registration stays in the test outbox; no real SMTP connection is made.
    monkeypatch.setattr(settings, "smtp_host", "")
    register(client, EMAIL, "CANDIDATE")
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "frontend_url", "https://jobs.example.org/")
    delivered = []

    def capture_delivery(to, subject, body):
        delivered.append({"to": to, "subject": subject, "body": body})
        raw = re.search(r"token=([\w-]+)", body).group(1)
        # A separate session must see the committed token before SMTP is called.
        with SessionLocal() as db:
            token = db.scalar(
                select(AuthToken).where(
                    AuthToken.token_hash == hashlib.sha256(raw.encode()).hexdigest(), AuthToken.purpose == "RESET"
                )
            )
            assert token is not None
            assert token.token_hash != raw
        return "sent"

    monkeypatch.setattr(auth_service, "deliver", capture_delivery)
    return client, delivered


def request_reset(recovery):
    client, delivered = recovery
    response = client.post(f"{API}/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200, response.text
    assert response.json()["delivery_mode"] == "EMAIL"
    assert "reset_url" not in response.json()
    assert "token" not in response.json()
    mail = delivered[-1]
    assert mail["to"] == EMAIL
    link = re.search(r"https://[^\s]+/reset-password\?token=[\w-]+", mail["body"]).group(0)
    parsed = urlsplit(link)
    assert parsed.scheme == "https"
    assert parsed.netloc == "jobs.example.org"
    assert parsed.path == "/reset-password"
    raw = parse_qs(parsed.query)["token"][0]
    assert raw not in response.text
    return raw


def test_emailed_link_changes_password_once_and_revokes_refresh_sessions(recovery, monkeypatch):
    client, _ = recovery
    previous = client.post(f"{API}/login", json={"email": EMAIL, "password": "123456"}).json()
    dispatched = []
    monkeypatch.setattr(send_email, "delay", lambda *args: dispatched.append(args))

    token = request_reset(recovery)
    assert dispatched == []  # Recovery must not wait for Redis or a Celery worker.
    response = client.post(f"{API}/reset-password", json={"token": token, "password": "new-password-123"})
    assert response.status_code == 200
    assert client.post(f"{API}/login", json={"email": EMAIL, "password": "123456"}).status_code == 401
    assert client.post(f"{API}/login", json={"email": EMAIL, "password": "new-password-123"}).status_code == 200
    assert client.post(f"{API}/refresh", json={"refresh_token": previous["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "second-password"}).status_code == 400


@pytest.mark.parametrize("dev_enabled", [False, True])
def test_missing_smtp_cannot_fall_back_to_a_demo_link(recovery, monkeypatch, dev_enabled):
    client, delivered = recovery
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "enable_dev_tools", dev_enabled)
    known = client.post(f"{API}/forgot-password", json={"email": EMAIL})
    unknown = client.post(f"{API}/forgot-password", json={"email": "unknown@t.vn"})
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json()
    assert "reset_url" not in known.json()
    assert "token" not in known.json()
    assert delivered == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuthToken).where(AuthToken.purpose == "RESET")) == 0


@pytest.mark.parametrize("missing_setting", ["smtp_user", "smtp_password"])
def test_gmail_requires_complete_credentials_before_creating_or_sending_a_reset(recovery, monkeypatch, missing_setting):
    client, delivered = recovery
    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(settings, "smtp_user", "sender@example.org")
    monkeypatch.setattr(settings, "smtp_password", "test-app-password")
    monkeypatch.setattr(settings, missing_setting, "")
    known = client.post(f"{API}/forgot-password", json={"email": EMAIL})
    unknown = client.post(f"{API}/forgot-password", json={"email": "unknown@t.vn"})
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json()
    assert "reset_url" not in known.json()
    assert "token" not in known.json()
    assert delivered == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuthToken).where(AuthToken.purpose == "RESET")) == 0


def test_smtp_response_is_generic_and_never_exposes_the_link_with_dev_tools_enabled(recovery, monkeypatch):
    client, delivered = recovery
    monkeypatch.setattr(settings, "enable_dev_tools", True)
    known = client.post(f"{API}/forgot-password", json={"email": EMAIL})
    unknown = client.post(f"{API}/forgot-password", json={"email": "unknown@t.vn"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert known.json()["delivery_mode"] == "EMAIL"
    assert "reset_url" not in known.json()
    assert "token" not in known.json()
    assert len(delivered) == 1
    token = re.search(r"token=([\w-]+)", delivered[0]["body"]).group(1)
    assert token not in known.text


@pytest.mark.parametrize("delivery_error", [OSError("SMTP unavailable"), smtplib.SMTPException("SMTP rejected")])
def test_smtp_delivery_failure_does_not_claim_success_or_expose_a_token(recovery, monkeypatch, delivery_error):
    client, _ = recovery

    def fail_delivery(*args):
        raise delivery_error

    monkeypatch.setattr(auth_service, "deliver", fail_delivery)
    response = client.post(f"{API}/forgot-password", json={"email": EMAIL})
    assert response.status_code == 503
    assert "reset_url" not in response.json()
    assert "token" not in response.json()
    assert response.json().get("ok") is not True
    assert str(delivery_error) not in response.text


@pytest.mark.parametrize("account_status", ["UNKNOWN", "LOCKED"])
def test_unknown_or_locked_accounts_do_not_receive_a_token_or_email(recovery, account_status):
    client, delivered = recovery
    if account_status == "LOCKED":
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email == EMAIL)).status = "LOCKED"
            db.commit()
    target = EMAIL if account_status == "LOCKED" else "unknown@t.vn"
    response = client.post(f"{API}/forgot-password", json={"email": target})
    assert response.status_code == 200
    assert response.json()["delivery_mode"] == "EMAIL"
    assert "reset_url" not in response.json()
    assert "token" not in response.json()
    assert delivered == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuthToken).where(AuthToken.purpose == "RESET")) == 0


def test_expired_reset_link_cannot_change_password(recovery):
    client, _ = recovery
    token = request_reset(recovery)
    with SessionLocal() as db:
        db.scalar(select(AuthToken).where(AuthToken.purpose == "RESET")).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "new-password-123"}).status_code == 400
    assert client.post(f"{API}/login", json={"email": EMAIL, "password": "123456"}).status_code == 200


def test_requesting_another_link_invalidates_the_previous_reset_link(recovery):
    client, _ = recovery
    previous = request_reset(recovery)
    current = request_reset(recovery)
    assert previous != current
    assert client.post(f"{API}/reset-password", json={"token": previous, "password": "new-password-123"}).status_code == 400
    assert client.post(f"{API}/reset-password", json={"token": current, "password": "new-password-123"}).status_code == 200


def test_email_verification_token_cannot_be_used_to_reset_password(recovery):
    client, _ = recovery
    verification_email = next(m for m in reversed(mailer.outbox) if m["to"] == EMAIL and "/verify-email?" in m["body"])
    verification_token = re.search(r"token=([\w-]+)", verification_email["body"]).group(1)
    response = client.post(f"{API}/reset-password", json={"token": verification_token, "password": "new-password-123"})
    assert response.status_code == 400
    assert client.post(f"{API}/login", json={"email": EMAIL, "password": "123456"}).status_code == 200


@pytest.mark.parametrize("invalid_password", ["12345", "\u0111" * 37])
def test_invalid_new_password_does_not_consume_the_reset_link(recovery, invalid_password):
    client, _ = recovery
    token = request_reset(recovery)
    response = client.post(f"{API}/reset-password", json={"token": token, "password": invalid_password})
    assert response.status_code == 422
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "valid-password-123"}).status_code == 200
