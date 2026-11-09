import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..ai.cv_parser import parse_cv_file, parse_cv_text
from ..ai.skills import normalize_skill_list, years_to_seniority
from ..config import settings
from ..models import CV, User
from ..repositories import cvs as queries
from ..schemas.cvs import CVUpdate
from ..services.common import audit, cv_out, embed_cv

MAX_FILE = 5 * 1024 * 1024


def _own_cv(db, user, cv_id) -> CV:
    cv = queries.get(db, cv_id)
    if not cv or cv.candidate_id != user.id:
        raise HTTPException(404, "Không tìm thấy CV")
    return cv


def _default_cv(db, user) -> CV | None:
    return queries.default_for_candidate(db, user)


def my_cvs(*, user: User, db: Session):
    return [cv_out(c) for c in queries.list_for_candidate(db, user)]


async def upload_cv(
    *, file: UploadFile | None = None, text: str | None = None, title: str | None = None, user: User, db: Session
):
    """Tải CV (PDF/DOCX) hoặc dán nội dung. Hệ thống trích xuất kỹ năng/kinh nghiệm và tạo embedding."""
    if file:
        name = file.filename or "cv"
        ext = name.rsplit(".", 1)[-1].lower()
        if ext not in ("pdf", "docx", "txt"):
            raise HTTPException(400, "Chỉ hỗ trợ PDF, DOCX hoặc TXT")
        data = await file.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise HTTPException(400, "File tối đa 5MB")
        try:
            parsed = parse_cv_file(data, name)
        except Exception:
            raise HTTPException(400, "Không đọc được file CV")
        file_path, file_type = (f"{uuid.uuid4().hex}.{ext}", ext)
    elif text and text.strip():
        parsed = {"raw_text": text, **parse_cv_text(text)}
        file_path, file_type = (None, "text")
    else:
        raise HTTPException(400, "Cần tải file hoặc dán nội dung CV")
    if len(parsed["raw_text"].strip()) < 50:
        raise HTTPException(400, "CV quá ngắn hoặc là ảnh scan (chưa hỗ trợ OCR)")
    if file:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        (settings.upload_dir / file_path).write_bytes(data)
    has_cv = queries.has_cv(db, user)
    cv = CV(
        candidate_id=user.id,
        title=title or parsed.get("title") or "CV của tôi",
        file_path=file_path,
        file_type=file_type,
        raw_text=parsed["raw_text"],
        parsed={k: parsed[k] for k in ("name", "title", "email", "phone", "sections", "experience", "major")},
        skills=parsed["skills"],
        years=parsed["years"],
        seniority=parsed["seniority"],
        role=parsed["role"],
        is_default=not has_cv,
    )
    queries.add(db, cv)
    db.flush()
    embed_cv(cv)
    audit(db, user, "CV_UPLOADED", "cv", cv.id, {"skills": len(cv.skills)})
    db.commit()
    return cv_out(cv, full=True)


def get_cv(*, cv_id: int, user: User, db: Session):
    return cv_out(_own_cv(db, user, cv_id), full=True)


def update_cv(*, cv_id: int, body: CVUpdate, user: User, db: Session):
    """Ứng viên sửa lại kết quả trích xuất nếu hệ thống đọc sai."""
    cv = _own_cv(db, user, cv_id)
    changed = False
    if body.title is not None:
        cv.title, changed = (body.title, True)
    if body.skills is not None:
        cv.skills, changed = (normalize_skill_list(body.skills), True)
    if body.years is not None:
        cv.years, cv.seniority, changed = (max(0, body.years), years_to_seniority(max(0, body.years)), True)
    if body.role:
        cv.role, changed = (body.role, True)
    if body.is_default:
        queries.clear_default(db, user)
        cv.is_default = True
    if changed:
        embed_cv(cv)
    db.commit()
    return cv_out(cv, full=True)


def delete_cv(*, cv_id: int, user: User, db: Session):
    cv = _own_cv(db, user, cv_id)
    if queries.is_used(db, cv):
        raise HTTPException(409, "CV đã dùng để ứng tuyển, không thể xóa")
    queries.delete(db, cv)
    db.commit()
    return {"ok": True}


def download_cv(*, cv_id: int, user: User, db: Session):
    cv = queries.get_for_download(db, cv_id)
    if not cv or not cv.file_path:
        raise HTTPException(404, "Không có file")
    allowed = (
        cv.candidate_id == user.id
        or user.role == "ADMIN"
        or (user.role == "HR" and queries.hr_can_access(db, cv, user))
    )
    if not allowed:
        raise HTTPException(403, "Bạn không có quyền xem CV này")
    return FileResponse(settings.upload_dir / cv.file_path, filename=f"cv_{cv.id}.{cv.file_type}")
