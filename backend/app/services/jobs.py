from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.skills import (
    extract_skills,
    min_years_from_text,
    normalize_role,
    normalize_skill_list,
    seniority_from_title,
    years_to_seniority,
)
from ..config import settings
from ..models import Job, User
from ..repositories import jobs as queries
from ..schemas.jobs import InviteIn, JobIn, JobStatusIn
from ..services.common import audit, aware, company_out, embed_job, job_out, now, slot_out
from ..services.payments import active_hr_subscription
from .companies import _company


def _own_job(db, user, job_id) -> Job:
    job = queries.get(db, job_id)
    if not job or job.company_id != _company(user).id:
        raise HTTPException(404, "Không tìm thấy tin tuyển dụng")
    return job


def _fill_job(job: Job, body: JobIn):
    job.title, job.description, job.city = (body.title, body.description, body.city)
    job.salary_min, job.salary_max = (body.salary_min, body.salary_max)
    job.skills = (
        normalize_skill_list(body.skills) if body.skills else extract_skills(body.title + "\n" + body.description)
    )
    years = body.min_years if body.min_years is not None else min_years_from_text(body.description) or 0
    job.min_years = years
    job.seniority = body.seniority or seniority_from_title(body.title) or years_to_seniority(years)
    job.role = body.role or normalize_role(body.title, body.title)
    if job.role == "other":
        job.role = "software_engineer"
    job.expires_at = now() + timedelta(days=max(1, min(body.expires_in_days, 90)))


def quota(*, user: User, db: Session):
    used_free = queries.count_posts_for_quota(db, _company(user)) or 0
    sub = active_hr_subscription(db, user.id)
    db.rollback()
    return {
        "free_limit": settings.free_job_posts,
        "free_used": min(used_free, settings.free_job_posts),
        "subscription": {
            "package": sub.package.name,
            "remaining": sub.remaining_quota,
            "ends_at": sub.ends_at.isoformat(),
        }
        if sub
        else None,
    }


def my_jobs(*, user: User, db: Session):
    c = _company(user)
    jobs = queries.list_owned(db, c)
    stats = {job_id: (count, avg) for job_id, count, avg in queries.application_counts(db, c)}
    return [
        {
            **job_out(j, full=False),
            "applications": stats.get(j.id, (0, None))[0],
            "avg_match_score": round(float(stats[j.id][1]), 4) if stats.get(j.id, (0, None))[1] is not None else None,
        }
        for j in jobs
    ]


def create_job(*, body: JobIn, user: User, db: Session):
    c = _company(user)
    if c.status != "APPROVED":
        raise HTTPException(409, "Công ty cần được quản trị viên duyệt trước khi đăng tin")
    source = _consume_quota(db, c, user) if body.submit else None
    job = Job(company_id=c.id, status="PENDING" if body.submit else "DRAFT")
    _fill_job(job, body)
    queries.add(db, job)
    db.flush()
    embed_job(job)
    audit(db, user, "JOB_CREATED", "job", job.id, {"quota": source, "status": job.status})
    db.commit()
    return job_out(job)


def _consume_quota(db, c, user) -> str:
    """Trừ lượt đăng khi tin được gửi duyệt: dùng lượt miễn phí trước, sau đó tới gói đăng tin."""
    posted = queries.count_posts(db, c) or 0
    if posted < settings.free_job_posts:
        return "FREE"
    sub = active_hr_subscription(db, user.id)
    if not sub:
        raise HTTPException(402, "Bạn đã dùng hết lượt đăng miễn phí. Vui lòng mua gói đăng tin.")
    sub.remaining_quota -= 1
    return f"SUB#{sub.id}"


def get_job(*, job_id: int, user: User, db: Session):
    return job_out(_own_job(db, user, job_id))


def update_job(*, job_id: int, body: JobIn, user: User, db: Session):
    job = _own_job(db, user, job_id)
    if job.status == "CLOSED":
        raise HTTPException(409, "Tin đã đóng")
    _fill_job(job, body)
    if job.status in ("PUBLISHED", "REJECTED"):
        job.status = "PENDING"
    embed_job(job)
    db.commit()
    return job_out(job)


def change_status(*, job_id: int, body: JobStatusIn, user: User, db: Session):
    """Đóng tin, gửi duyệt bản nháp hoặc mở lại tin đã đóng. Mọi thay đổi được ghi audit log."""
    job = _own_job(db, user, job_id)
    frm = job.status
    if body.status == "CLOSED":
        if frm == "CLOSED":
            raise HTTPException(409, "Tin đã đóng")
        job.status = "CLOSED"
    elif frm == "DRAFT":
        _consume_quota(db, job.company, user)
        job.status = "PENDING"
    elif frm == "CLOSED":
        if job.expires_at and aware(job.expires_at) <= now() and not body.expires_in_days:
            raise HTTPException(400, "Tin đã hết hạn, vui lòng chọn thời hạn hiển thị mới")
        if body.expires_in_days:
            job.expires_at = now() + timedelta(days=body.expires_in_days)
        # Mở lại cần quản trị viên duyệt lại trước khi công khai (BR-21).
        job.status = "PENDING"
    else:
        raise HTTPException(409, "Chỉ gửi duyệt bản nháp hoặc mở lại tin đã đóng")
    audit(db, user, "JOB_STATUS", "job", job.id, {"from": frm, "to": job.status})
    db.commit()
    return job_out(job)


def invite_candidate(*, job_id: int, body: InviteIn, user: User, db: Session):
    """HR mời ứng viên (thường là người được AI gợi ý) nộp hồ sơ: gửi thông báo kèm link tin."""
    job = _own_job(db, user, job_id)
    if job.status != "PUBLISHED":
        raise HTTPException(409, "Chỉ mời ứng tuyển cho tin đang hiển thị")
    cand = queries.find_candidate(db, body)
    if not cand or cand.role != "CANDIDATE" or cand.status != "ACTIVE":
        raise HTTPException(404, "Không tìm thấy ứng viên")
    if queries.has_application(db, cand, job):
        raise HTTPException(409, "Ứng viên đã ứng tuyển tin này")
    link = f"/jobs/{job.id}"
    if queries.find_invitation(db, cand, link):
        raise HTTPException(409, "Đã mời ứng viên này rồi")
    note = f": {body.message.strip()[:200]}" if body.message and body.message.strip() else ""
    queries.add_invitation(db, cand, job, link, note)
    audit(db, user, "JOB_INVITE", "job", job.id, {"candidate": cand.id})
    db.commit()
    return {"ok": True}


def stats(*, user: User, db: Session):
    c = _company(user)
    by_status = dict(queries.application_status_counts(db, c))
    jobs = dict(queries.job_status_counts(db, c))
    upcoming = queries.upcoming_slots(db, user)
    apps = {a.id: a for a in queries.applications_for_slots(db, upcoming)}
    items = []
    for s in upcoming:
        a = apps.get(s.application_id)
        items.append(
            {
                **slot_out(s),
                "candidate_name": a.candidate.full_name if a else None,
                "job_title": a.job.title if a else None,
            }
        )
    return {
        "applications_by_status": by_status,
        "jobs_by_status": jobs,
        "upcoming_interviews": items,
        "total_cvs_in_pool": queries.cv_pool_count(db),
    }


def search_jobs(
    *,
    q: str | None = None,
    role: str | None = None,
    city: str | None = None,
    seniority: str | None = None,
    skill: str | None = None,
    company_id: int | None = None,
    cities: list[str] | None = None,
    salary_range: str | None = None,
    experience: list[str] | None = None,
    sort: str = "newest",
    page: int = 1,
    size: int = 20,
    db: Session,
):
    stmt = queries.open_jobs()
    if q:
        like = f"%{q.strip()}%"
        stmt = queries.filter_keyword(like, stmt)
    if role:
        stmt = queries.filter_role(role, stmt)
    selected_cities = [*(cities or []), *([city] if city else [])]
    if selected_cities:
        stmt = queries.filter_cities(selected_cities, stmt)
    if seniority:
        stmt = queries.filter_seniority(seniority, stmt)
    if company_id:
        stmt = queries.filter_company(company_id, stmt)
    if skill:
        stmt = queries.filter_skill(skill, stmt)
    if salary_range:
        stmt = queries.filter_salary_range(salary_range, stmt)
    if experience:
        stmt = queries.filter_experience(experience, stmt)
    total = queries.count(db, stmt)
    rows = queries.list_page(db, page, size, stmt, sort=sort)
    return {"total": total, "page": page, "size": size, "items": [job_out(j, full=False) for j in rows]}


def job_detail(*, job_id: int, db: Session, user):
    job = queries.get_public(db, job_id)
    if not job:
        raise HTTPException(404, "Không tìm thấy tin tuyển dụng")
    is_owner = user and user.role == "HR" and (job.company.owner_id == user.id)
    is_admin = bool(user and user.role == "ADMIN")
    if job.status != "PUBLISHED" and (not is_owner) and (not is_admin):
        raise HTTPException(404, "Tin tuyển dụng không còn hiển thị")
    if not is_owner and not is_admin:
        queries.increment_views(db, job)
        db.commit()
        db.refresh(job)
    return {**job_out(job), "company": company_out(job.company)}
