"""Real mail delivery must use verified TLS and keep recovery text in the email."""

import ssl
from unittest.mock import MagicMock

from app.config import settings
from app.core import mailer


def test_gmail_delivery_verifies_tls_uses_app_password_and_preserves_vietnamese_email(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_tls", True)
    monkeypatch.setattr(settings, "smtp_user", "jobmatch-test@gmail.com")
    monkeypatch.setattr(settings, "smtp_password", "abcd efgh ijkl mnop")
    monkeypatch.setattr(settings, "smtp_from", "")
    server = MagicMock()
    server.__enter__.return_value = server
    factory = MagicMock(return_value=server)
    monkeypatch.setattr(mailer.smtplib, "SMTP", factory)

    result = mailer.deliver("recipient@example.com", "Đặt lại mật khẩu JobMatch", "Liên kết có hiệu lực 30 phút.")

    assert result == "sent"
    factory.assert_called_once_with("smtp.gmail.com", 587, timeout=20)
    tls_context = server.starttls.call_args.kwargs["context"]
    assert tls_context.verify_mode == ssl.CERT_REQUIRED
    assert tls_context.check_hostname is True
    server.login.assert_called_once_with("jobmatch-test@gmail.com", "abcdefghijklmnop")
    email = server.send_message.call_args.args[0]
    assert email["From"] == "JobMatch <jobmatch-test@gmail.com>"
    assert email["To"] == "recipient@example.com"
    assert email["Subject"] == "Đặt lại mật khẩu JobMatch"
    assert "Liên kết có hiệu lực 30 phút." in email.get_content()
    server.__exit__.assert_called_once()
