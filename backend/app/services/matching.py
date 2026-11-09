from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.cv_evaluation import evaluate
from ..ai.matcher import match_pair, rank_cvs_for_job, rank_jobs_for_cv
from ..models import User
from ..repositories import matching as queries
from ..services.common import aware, cv_out, is_premium, job_out, now
from .cvs import _default_cv, _own_cv
from .jobs import _own_job


def _is_premium(u: User) -> bool:
    return is_premium(u)


def recommendations(*, cv_id: int | None = None, user: User, db: Session):
    cv = _own_cv(db, user, cv_id) if cv_id else _default_cv(db, user)
    if not cv:
        raise HTTPException(400, "Bạn cần tải CV lên trước")
    if not cv.embedding:
        raise HTTPException(409, "CV đang được xử lý, vui lòng thử lại sau")
    premium = _is_premium(user)
    k = 30
    applied = set(queries.applied_job_ids(db, user))
    items = []
    for job, exp in rank_jobs_for_cv(db, cv, k=k):
        if not premium:
            exp = {k2: exp[k2] for k2 in ("score", "matched_skills", "missing_skills")}
        items.append({"job": job_out(job, full=False), "match": exp, "applied": job.id in applied})
    return {"cv": cv_out(cv), "premium": premium, "items": items, "limit_note": None}


def match_one(*, job_id: int, cv_id: int | None = None, user: User, db: Session):
    """Phân tích mức phù hợp của CV với 1 tin (gap analysis)."""
    job = queries.get_job(db, job_id)
    cv = _own_cv(db, user, cv_id) if cv_id else _default_cv(db, user)
    if not job or not cv:
        raise HTTPException(404, "Thiếu tin tuyển dụng hoặc CV")
    if job.status != "PUBLISHED" or (job.expires_at and aware(job.expires_at) <= now()):
        raise HTTPException(404, "Tin tuyển dụng không còn hiển thị")
    if not job.embedding or not cv.embedding:
        raise HTTPException(409, "Dữ liệu chưa sẵn sàng")
    exp = match_pair(job, cv)
    premium = _is_premium(user)
    if not premium:
        exp = {k: exp[k] for k in ("score", "matched_skills", "missing_skills")}
    return {"cv": cv_out(cv), "match": exp, "premium": premium}


def cv_evaluation(*, cv_id: int, user: User, db: Session, job_id: int | None = None):
    if not _is_premium(user):
        raise HTTPException(403, "Đánh giá CV chuyên sâu yêu cầu gói Premium còn hiệu lực")
    cv = _own_cv(db, user, cv_id)
    job = queries.get_job(db, job_id) if job_id else None
    match = None
    if job_id:
        if not job or job.status != "PUBLISHED" or (job.expires_at and aware(job.expires_at) <= now()):
            raise HTTPException(404, "Không tìm thấy tin tuyển dụng đang mở")
        if not cv.embedding or not job.embedding:
            raise HTTPException(409, "Dữ liệu đang được xử lý, vui lòng thử lại sau")
        match = match_pair(job, cv)
    return evaluate(cv, job, match)


def recommended_candidates(*, job_id: int, limit: int = 30, user: User, db: Session):
    """Tìm CV phù hợp nhất trong toàn bộ kho CV (kể cả người chưa ứng tuyển) - chiều HR -> ứng viên."""
    job = _own_job(db, user, job_id)
    applied = set(queries.applied_candidate_ids(db, job))
    invited = set(queries.invited_candidate_ids(db, job))
    ranked = rank_cvs_for_job(db, job, k=min(limit, 100) * 2)
    out, seen = ([], set())
    for cv, exp in ranked:
        if cv.candidate_id in seen:
            continue
        seen.add(cv.candidate_id)
        has_applied = cv.candidate_id in applied
        summary = cv_out(cv)
        if not has_applied:
            summary["title"] = f"Hồ sơ #{cv.id}"
        name = cv.candidate.full_name if has_applied else f"Ứng viên #{cv.candidate_id}"
        out.append(
            {
                "cv": summary,
                "candidate": {"id": cv.candidate.id, "full_name": name},
                "match": exp,
                "applied": has_applied,
                "invited": cv.candidate_id in invited,
            }
        )
        if len(out) >= limit:
            break
    return out


def gap(*, cv_id: int, job_id: int, user: User, db: Session):
    """Phân tích kỹ năng khớp/thiếu. HR chỉ xem được CV đã ứng tuyển vào tin của mình (BR-20)."""
    if user.role == "CANDIDATE":
        return match_one(job_id=job_id, cv_id=cv_id, user=user, db=db)
    job = _own_job(db, user, job_id)
    if not queries.applied_with_cv(db, job, cv_id):
        raise HTTPException(403, "Chỉ xem phân tích cho CV đã ứng tuyển vào tin của bạn")
    cv = queries.get_cv(db, cv_id)
    if not job.embedding or not cv or not cv.embedding:
        raise HTTPException(409, "Dữ liệu chưa sẵn sàng")
    return {"cv": cv_out(cv), "match": match_pair(job, cv), "premium": True}
