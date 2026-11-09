"""Check SMTP configuration and optional authentication without sending an email."""

import argparse
import smtplib
import sys
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.core.mailer import open_smtp  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", action="store_true", help="Verify STARTTLS and SMTP login; do not send any email")
    args = parser.parse_args()
    errors = []
    for name, value in (("SMTP_HOST", settings.smtp_host), ("SMTP_USER", settings.smtp_user), ("SMTP_PASSWORD", settings.smtp_password)):
        if not value.strip():
            errors.append(f"Missing {name}; set it in .env")
    sender = parseaddr(settings.smtp_from.strip() or f"JobMatch <{settings.smtp_user.strip()}>")[1]
    if "@" not in sender or sender.endswith(".local"):
        errors.append("SMTP_FROM must contain a real sender email address")
    website = urlsplit(settings.frontend_url)
    if website.scheme not in ("http", "https") or not website.netloc:
        errors.append("FRONTEND_URL must be the website URL opened by users")
    if settings.smtp_host.strip().lower() == "smtp.gmail.com":
        if settings.smtp_port != 587 or not settings.smtp_tls:
            errors.append("Gmail configuration requires SMTP_PORT=587 and SMTP_TLS=true")
        if settings.smtp_password and len("".join(settings.smtp_password.split())) != 16:
            errors.append("SMTP_PASSWORD must be a 16-character Gmail app password")
        if sender.lower() != settings.smtp_user.strip().lower():
            errors.append("For this Gmail setup, SMTP_FROM must match SMTP_USER")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("SMTP configuration is complete; credentials are not displayed.")
    if args.connect:
        try:
            with open_smtp() as smtp:
                status, _ = smtp.noop()
                if status != 250:
                    print("ERROR: SMTP server did not accept the connection check")
                    return 1
        except smtplib.SMTPAuthenticationError:
            print("ERROR: SMTP login failed; check SMTP_USER and the Gmail app password")
            return 1
        except (OSError, smtplib.SMTPException):
            print("ERROR: Cannot connect to SMTP; check network, host, port and TLS settings")
            return 1
        print("SMTP connection, TLS and authentication succeeded. No email was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
