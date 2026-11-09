"""Gửi email qua SMTP. Khi chưa cấu hình SMTP_HOST, email chỉ được ghi log và lưu vào `outbox` (dev/test)."""

import logging
import smtplib
import ssl
from contextlib import contextmanager
from email.message import EmailMessage

from sqlalchemy.orm import Session

from ..config import settings

log = logging.getLogger(__name__)
outbox: list[dict] = []


@contextmanager
def open_smtp():
    """Mở kết nối SMTP đã xác thực để gửi thư hoặc kiểm tra kết nối."""
    with smtplib.SMTP(settings.smtp_host.strip(), settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            password = settings.smtp_password
            if settings.smtp_host.strip().lower() == "smtp.gmail.com":
                password = "".join(password.split())
            smtp.login(settings.smtp_user.strip(), password)
        yield smtp


def deliver(to: str, subject: str, body: str) -> str:
    if not settings.smtp_host:
        outbox.append({"to": to, "subject": subject, "body": body})
        # WARNING để luôn hiện trong log uvicorn/celery mặc định: dev lấy liên kết xác minh/đặt lại mật khẩu tại đây.
        log.warning("Email (chưa cấu hình SMTP) tới %s: %s\n%s", to, subject, body)
        return "logged"
    msg = EmailMessage()
    sender = settings.smtp_from.strip() or f"JobMatch <{settings.smtp_user.strip()}>"
    msg["From"], msg["To"], msg["Subject"] = (sender, to, subject)
    msg.set_content(body)
    with open_smtp() as smtp:
        smtp.send_message(msg)
    return "sent"


def queue_email(db: Session, to: str, subject: str, body: str):
    """Đưa email vào hàng đợi; chỉ gửi sau khi transaction commit thành công."""
    db.info.setdefault("email_tasks", []).append((to, subject, body))
