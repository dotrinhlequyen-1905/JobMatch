"""Hàm dùng chung: embedding cho JD/CV, thông báo, audit log, chuyển object -> dict."""

from sqlalchemy.orm import Session, object_session

from ..ai.embedder import cv_profile, get_embedder, jd_profile, to_bytes
from ..ai.skills import ROLE_DISPLAY
from ..config import settings
from ..core.clock import aware, now
from ..core.company_logos import resolve_company_logo_url
from ..models import CV, Application, Company, InterviewSlot, Job, Order, Package, Refund, User
from ..repositories import common as queries
from ..state_machines import APP_STATUS_VI, allowed_next


def job_text(job: Job) -> str:
    return jd_profile(job.title, job.role, job.seniority, job.min_years, job.skills or [])


def cv_text(cv: CV) -> str:
    p = cv.parsed or {}
    return cv_profile(cv.title, cv.seniority, cv.years, cv.skills or [], p.get("experience", []), p.get("major", ""))


def embed_job(job: Job):
    schedule_embedding(job, "job", job_text)


def embed_cv(cv: CV):
    schedule_embedding(cv, "cv", cv_text)


def schedule_embedding(entity, kind, text_fn):
    entity.embedding_revision = (entity.embedding_revision or 0) + 1
    entity.embedding = None
    entity.processing_status = "PENDING"
    entity.embedding_model = ""
    if settings.task_always_eager:
        entity.embedding = to_bytes(get_embedder().encode([text_fn(entity)])[0])
        entity.processing_status = "READY"
        entity.embedding_model = get_embedder().name
        return
    session = object_session(entity)
    if session is None:
        raise ValueError("Embedding must be scheduled inside a database transaction")
    session.info.setdefault("embedding_tasks", []).append((kind, entity.id, entity.embedding_revision))


def notify(db: Session, user_id: int, type_: str, title: str, link: str | None = None):
    queries.add_notification(db, link, title, type_, user_id)


def audit(db: Session, actor: User | None, action: str, entity: str, entity_id: int | None, data: dict | None = None):
    queries.add_audit_log(db, action, actor, data, entity, entity_id)


def iso(dt):
    return aware(dt).isoformat() if dt else None


def user_out(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "phone": u.phone,
        "role": u.role,
        "status": u.status,
        "premium_until": iso(u.premium_until),
        "is_premium": is_premium(u),
        "email_verified": u.email_verified_at is not None,
        "avatar_url": f"/api/v1/users/{u.id}/avatar?v={u.avatar_path.rsplit('/', 1)[-1][:8]}" if u.avatar_path else None,
        "created_at": iso(u.created_at),
    }


def is_premium(user: User) -> bool:
    if user.role != "CANDIDATE" or not user.premium_until or aware(user.premium_until) <= now():
        return False
    db = object_session(user)
    return db is not None and queries.has_active_premium(db, user.id)


def company_out(c: Company, with_owner=False, *, resolve_logo=True) -> dict:
    d = {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "location": c.location,
        "website": c.website,
        "logo_url": resolve_company_logo_url(c.name, c.logo_url) if resolve_logo else c.logo_url,
        "status": c.status,
        "created_at": iso(c.created_at),
    }
    if with_owner:
        d["owner"] = {"id": c.owner.id, "email": c.owner.email, "full_name": c.owner.full_name}
    return d


def job_out(j: Job, full=True) -> dict:
    d = {
        "id": j.id,
        "title": j.title,
        "role": j.role,
        "role_display": ROLE_DISPLAY.get(j.role, (j.role,))[0],
        "seniority": j.seniority,
        "min_years": j.min_years,
        "skills": j.skills or [],
        "city": j.city,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "status": j.status,
        "expires_at": iso(j.expires_at),
        "created_at": iso(j.created_at),
        "processing_status": j.processing_status,
        "view_count": j.view_count or 0,
        "company": {
            "id": j.company.id,
            "name": j.company.name,
            "logo_url": resolve_company_logo_url(j.company.name, j.company.logo_url),
        },
    }
    if full:
        d["description"] = j.description
    return d


def cv_out(c: CV, full=False) -> dict:
    d = {
        "id": c.id,
        "title": c.title,
        "file_type": c.file_type,
        "skills": c.skills or [],
        "years": c.years,
        "seniority": c.seniority,
        "role": c.role,
        "role_display": ROLE_DISPLAY.get(c.role, (c.role,))[0],
        "is_default": c.is_default,
        "created_at": iso(c.created_at),
        "has_file": bool(c.file_path),
        "processing_status": c.processing_status,
    }
    if full:
        d["raw_text"] = c.raw_text
        d["parsed"] = c.parsed
    return d


def app_out(a: Application, viewer_role: str) -> dict:
    return {
        "id": a.id,
        "status": a.status,
        "status_vi": APP_STATUS_VI[a.status],
        "match_score": a.match_score,
        "cover_letter": a.cover_letter,
        "created_at": iso(a.created_at),
        "updated_at": iso(a.updated_at),
        "job": job_out(a.job, full=False),
        "candidate": {
            "id": a.candidate.id,
            "full_name": a.candidate.full_name,
            "email": a.candidate.email,
            "phone": a.candidate.phone,
        },
        "cv": cv_out(a.cv),
        "next_actions": allowed_next(a.status, viewer_role),
        "history": [
            {"from": h.from_status, "to": h.to_status, "note": h.note, "at": iso(h.created_at)} for h in a.history
        ],
    }


def slot_out(s: InterviewSlot) -> dict:
    return {
        "id": s.id,
        "job_id": s.job_id,
        "start_at": iso(s.start_at),
        "end_at": iso(s.end_at),
        "location": s.location,
        "status": s.status,
        "held_by": s.held_by,
        "held_until": iso(s.held_until),
        "application_id": s.application_id,
        "result": s.result,
        "feedback": s.feedback,
    }


def package_out(p: Package) -> dict:
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "target": p.target,
        "price": p.price,
        "duration_days": p.duration_days,
        "quota_jobs": p.quota_jobs,
        "description": p.description,
    }


def order_out(o: Order, refund: Refund | None = None) -> dict:
    from .payments import qr_url

    return {
        "id": o.id,
        "order_code": o.order_code,
        "amount": o.amount,
        "status": o.status,
        "expires_at": iso(o.expires_at),
        "paid_at": iso(o.paid_at),
        "created_at": iso(o.created_at),
        "package": package_out(o.package),
        "qr_url": qr_url(o) if o.status == "PENDING" else None,
        "user": {"id": o.user.id, "email": o.user.email, "full_name": o.user.full_name},
        "refund": {"id": refund.id, "status": refund.status, "reason": refund.reason, "admin_note": refund.admin_note}
        if refund
        else None,
    }
