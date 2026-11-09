import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..core.security import hash_password, verify_password
from ..models import CandidateProfile, User
from ..repositories import users as queries
from ..schemas.auth import CandidateProfileIn, ProfileIn
from ..services.common import audit, company_out, iso, user_out
from .auth import issue_session, revoke_sessions

MAX_AVATAR = 2 * 1024 * 1024
IMAGE_SIGNATURES = {"png": (b"\x89PNG",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",), "webp": (b"RIFF",)}


def me(*, user: User, db: Session):
    out = {"user": user_out(user)}
    if user.role == "HR" and user.company:
        out["company"] = company_out(user.company)
    return out


def update_me(*, body: ProfileIn, user: User, db: Session):
    if body.full_name:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    session = None
    if body.password:
        if not body.current_password or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng")
        user.password_hash = hash_password(body.password)
        # Đổi mật khẩu thu hồi mọi phiên cũ; phiên hiện tại nhận cặp token mới.
        revoke_sessions(db, user)
        session = issue_session(db, user)
        audit(db, user, "PASSWORD_CHANGED", "user", user.id)
    db.commit()
    return {"user": user_out(user), **({"token": session["token"], "refresh_token": session["refresh_token"]} if session else {})}


async def store_image(file: UploadFile, folder: str) -> str:
    """Kiểm tra định dạng/kích thước ảnh rồi lưu vào `upload_dir/folder`; trả về đường dẫn tương đối."""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in IMAGE_SIGNATURES:
        raise HTTPException(400, "Ảnh phải là PNG, JPG hoặc WEBP")
    data = await file.read(MAX_AVATAR + 1)
    if len(data) > MAX_AVATAR:
        raise HTTPException(400, "Ảnh tối đa 2MB")
    if not data.startswith(IMAGE_SIGNATURES[ext]):
        raise HTTPException(400, "Nội dung file không phải ảnh hợp lệ")
    (settings.upload_dir / folder).mkdir(parents=True, exist_ok=True)
    name = f"{folder}/{uuid.uuid4().hex}.{ext}"
    (settings.upload_dir / name).write_bytes(data)
    return name


async def upload_avatar(*, file: UploadFile, user: User, db: Session):
    name = await store_image(file, "avatars")
    old = user.avatar_path
    user.avatar_path = name
    db.commit()
    if old:
        (settings.upload_dir / old).unlink(missing_ok=True)
    return {"user": user_out(user)}


def avatar(*, user_id: int, db: Session):
    u = queries.get_user(db, user_id)
    if not u or not u.avatar_path or not (settings.upload_dir / u.avatar_path).is_file():
        raise HTTPException(404, "Chưa có ảnh đại diện")
    return FileResponse(settings.upload_dir / u.avatar_path)


def profile_out(p: CandidateProfile | None) -> dict:
    if not p:
        return {"headline": None, "summary": None, "location": None, "desired_role": None,
                "expected_salary": None, "is_public": True, "updated_at": None}
    return {
        "headline": p.headline,
        "summary": p.summary,
        "location": p.location,
        "desired_role": p.desired_role,
        "expected_salary": p.expected_salary,
        "is_public": p.is_public,
        "updated_at": iso(p.updated_at),
    }


def my_profile(*, user: User, db: Session):
    return profile_out(queries.get_profile(db, user))


def update_profile(*, body: CandidateProfileIn, user: User, db: Session):
    p = queries.get_profile(db, user)
    if not p:
        p = CandidateProfile(user_id=user.id)
        queries.add_profile(db, p)
    for k, v in body.model_dump().items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    audit(db, user, "PROFILE_UPDATED", "user", user.id, {"is_public": body.is_public})
    db.commit()
    return profile_out(p)
