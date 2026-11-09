"""Xác thực JWT + phân quyền theo vai trò (RBAC)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from ..repositories import security_core as queries
from .database import get_db

bearer = HTTPBearer(auto_error=False)


def hash_password(pw: str) -> str:
    if len(pw.encode()) > 72:
        raise HTTPException(422, "Mật khẩu không được vượt quá 72 byte UTF-8")
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def _user_from_token(creds, db) -> User | None:
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
        int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ hoặc đã hết hạn")
    user = queries.get_authenticated_user(db, payload)
    if not user or user.status != "ACTIVE":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khóa")
    return user


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = _user_from_token(creds, db)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cần đăng nhập")
    return user


def optional_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    return _user_from_token(creds, db)


def require_roles(*roles: str):

    def dep(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if user.role not in roles:
            # FR-1.5: ghi nhận thao tác vượt quyền để quản trị viên truy vết.
            queries.log_denied(db, user, request.method, request.url.path, roles)
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền thực hiện thao tác này")
        return user

    return dep


is_candidate = require_roles("CANDIDATE")
is_hr = require_roles("HR")
is_admin = require_roles("ADMIN")
