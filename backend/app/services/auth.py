"""Đăng ký, đăng nhập, phiên (access JWT + refresh token xoay vòng), khôi phục mật khẩu, xác minh email."""

import hashlib
import logging
import secrets
import smtplib
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..core.mailer import deliver, queue_email
from ..core.security import create_token, hash_password, verify_password
from ..models import AuthToken, User
from ..repositories import auth as queries
from ..schemas.auth import ForgotPasswordIn, LoginIn, RefreshIn, RegisterIn, ResetPasswordIn, TokenIn
from ..services.common import audit, aware, company_out, now, user_out

log = logging.getLogger(__name__)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_token(db: Session, user: User, purpose: str, ttl: timedelta) -> str:
    raw = secrets.token_urlsafe(32)
    queries.add_token(db, AuthToken(user_id=user.id, purpose=purpose, token_hash=_hash(raw), expires_at=now() + ttl))
    return raw


def _consume(db: Session, raw: str, purpose: str) -> AuthToken:
    token = queries.lock_token(db, _hash(raw), purpose)
    if not token or token.used_at or aware(token.expires_at) <= now():
        raise HTTPException(400, "Liên kết không hợp lệ hoặc đã hết hạn")
    token.used_at = now()
    return token


def issue_session(db: Session, user: User) -> dict:
    """Cấp access token (JWT) + refresh token mới. Nơi gọi commit."""
    refresh = new_token(db, user, "REFRESH", timedelta(days=settings.refresh_token_days))
    out = {"token": create_token(user), "refresh_token": refresh, "user": user_out(user)}
    if user.role == "HR" and user.company:
        out["company"] = company_out(user.company)
    return out


def revoke_sessions(db: Session, user: User):
    queries.revoke_tokens(db, user.id, "REFRESH")


def send_verification(db: Session, user: User):
    queries.revoke_tokens(db, user.id, "VERIFY")
    raw = new_token(db, user, "VERIFY", timedelta(hours=settings.verify_token_hours))
    link = f"{settings.frontend_url}/verify-email?token={raw}"
    queue_email(
        db,
        user.email,
        "Xác minh email tài khoản JobMatch",
        f"Chào {user.full_name},\n\nVui lòng xác minh email bằng liên kết sau (hiệu lực "
        f"{settings.verify_token_hours} giờ):\n{link}\n\nNếu bạn không đăng ký JobMatch, hãy bỏ qua email này.",
    )


def register(*, body: RegisterIn, db: Session):
    if queries.find_registered_email(db, body):
        raise HTTPException(409, "Email đã được sử dụng")
    if body.role == "HR" and (not (body.company_name or "").strip()):
        raise HTTPException(400, "Nhà tuyển dụng cần nhập tên công ty")
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        role=body.role,
    )
    queries.add_user(db, user)
    db.flush()
    if body.role == "HR":
        queries.add_company(db, body, user)
    send_verification(db, user)
    audit(db, user, "REGISTER", "user", user.id, {"role": body.role})
    db.flush()
    db.refresh(user)
    if settings.require_email_verification:
        db.commit()
        return {"user": user_out(user), "verification_required": True}
    out = issue_session(db, user)
    db.commit()
    return out


def login(*, body: LoginIn, db: Session):
    user = queries.find_login_email(db, body)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Sai email hoặc mật khẩu")
    if user.status != "ACTIVE":
        raise HTTPException(403, "Tài khoản đã bị khóa")
    if settings.require_email_verification and not user.email_verified_at:
        raise HTTPException(403, "Vui lòng xác minh email trước khi đăng nhập")
    out = issue_session(db, user)
    audit(db, user, "LOGIN", "user", user.id)
    db.commit()
    return out


def refresh(*, body: RefreshIn, db: Session):
    token = queries.lock_token(db, _hash(body.refresh_token), "REFRESH")
    if not token or aware(token.expires_at) <= now():
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    if token.used_at:
        # Refresh token cũ bị dùng lại: có thể đã lộ, thu hồi toàn bộ phiên của người dùng.
        revoke_sessions(db, token.user)
        audit(db, token.user, "REFRESH_REUSE", "user", token.user_id)
        db.commit()
        raise HTTPException(401, "Phiên đăng nhập không còn hiệu lực")
    if token.user.status != "ACTIVE":
        raise HTTPException(401, "Tài khoản đã bị khóa")
    token.used_at = now()
    out = issue_session(db, token.user)
    db.commit()
    return out


def logout(*, body: RefreshIn, db: Session):
    token = queries.lock_token(db, _hash(body.refresh_token), "REFRESH")
    if token and not token.used_at:
        token.used_at = now()
        audit(db, token.user, "LOGOUT", "user", token.user_id)
    db.commit()
    return {"ok": True}


def forgot_password(*, body: ForgotPasswordIn, db: Session):
    """Gửi liên kết qua email thật; không trả token khôi phục trong phản hồi API."""
    if not settings.smtp_host:
        raise HTTPException(503, "Dịch vụ gửi email chưa khả dụng. Vui lòng thử lại sau hoặc liên hệ quản trị viên")
    if settings.smtp_host.strip().lower() == "smtp.gmail.com" and not (settings.smtp_user and settings.smtp_password):
        raise HTTPException(503, "Dịch vụ gửi email chưa khả dụng. Vui lòng thử lại sau hoặc liên hệ quản trị viên")
    response = {
        "ok": True,
        "message": "Nếu email đã được đăng ký, hướng dẫn đặt lại mật khẩu đã được gửi. Vui lòng kiểm tra cả thư mục thư rác.",
        "delivery_mode": "EMAIL",
    }
    user = queries.find_user_by_email(db, body.email)
    if user and user.status == "ACTIVE":
        queries.revoke_tokens(db, user.id, "RESET")
        raw = new_token(db, user, "RESET", timedelta(minutes=settings.reset_token_minutes))
        audit(db, user, "PASSWORD_RESET_REQUESTED", "user", user.id)
        # Lưu token trước khi gửi; khôi phục mật khẩu không phụ thuộc Redis/Celery.
        db.commit()
        link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw}"
        try:
            deliver(
                user.email,
                "Đặt lại mật khẩu JobMatch",
                f"Chào {user.full_name},\n\nBạn vừa yêu cầu đặt lại mật khẩu. Liên kết sau có hiệu lực "
                f"{settings.reset_token_minutes} phút và chỉ dùng được một lần:\n{link}\n\n"
                "Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.",
            )
        except (OSError, smtplib.SMTPException):
            log.exception("Không gửi được email đặt lại mật khẩu")
            raise HTTPException(503, "Chưa gửi được email đặt lại mật khẩu. Vui lòng thử lại sau") from None
    return response


def reset_password(*, body: ResetPasswordIn, db: Session):
    token = _consume(db, body.token, "RESET")
    user = token.user
    user.password_hash = hash_password(body.password)
    revoke_sessions(db, user)
    audit(db, user, "PASSWORD_RESET", "user", user.id)
    db.commit()
    return {"ok": True}


def verify_email(*, body: TokenIn, db: Session):
    token = _consume(db, body.token, "VERIFY")
    if not token.user.email_verified_at:
        token.user.email_verified_at = now()
    audit(db, token.user, "EMAIL_VERIFIED", "user", token.user_id)
    db.commit()
    return {"ok": True, "user": user_out(token.user)}


def resend_verification(*, user: User, db: Session):
    if user.email_verified_at:
        raise HTTPException(409, "Email đã được xác minh")
    send_verification(db, user)
    db.commit()
    return {"ok": True}
