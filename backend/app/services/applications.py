import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..ai.matcher import match_pair, pair_ready
from ..models import Application, User
from ..repositories import applications as queries
from ..schemas.applications import ApplyIn, TransitionIn
from ..services.common import app_out, audit, aware, cv_out, notify, now, slot_out
from ..state_machines import APP_STATUSES, transition_application
from .companies import _company
from .cvs import _default_cv, _own_cv
from .jobs import _own_job

log = logging.getLogger(__name__)


def optional_match(job, cv):
    try:
        return match_pair(job, cv) if pair_ready(job, cv) else None
    except Exception:
        log.exception("Optional AI scoring failed for job %s / CV %s", job.id, cv.id)
        return None


def apply(*, body: ApplyIn, user: User, db: Session):
    job = queries.job_for_application(db, body)
    if not job or job.status != "PUBLISHED":
        raise HTTPException(404, "Tin tuyển dụng không còn nhận hồ sơ")
    if job.expires_at and aware(job.expires_at) < now():
        raise HTTPException(409, "Tin tuyển dụng đã hết hạn")
    cv = _own_cv(db, user, body.cv_id) if body.cv_id else _default_cv(db, user)
    if not cv:
        raise HTTPException(400, "Bạn cần tải CV lên trước khi ứng tuyển")
    match = optional_match(job, cv)
    score = match["score"] if match else None
    app = Application(
        job_id=job.id, candidate_id=user.id, cv_id=cv.id, match_score=score, cover_letter=body.cover_letter
    )
    queries.add(db, app)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bạn đã ứng tuyển tin này rồi")
    queries.add_initial_history(db, app, user)
    notify(
        db,
        job.company.owner_id,
        "APPLICATION",
        f"Hồ sơ mới cho '{job.title}' từ {user.full_name}",
        f"/hr/jobs/{job.id}",
    )
    audit(db, user, "APPLIED", "application", app.id, {"job": job.id, "score": score})
    db.commit()
    db.refresh(app)
    return app_out(app, "CANDIDATE")


def my_applications(*, user: User, db: Session):
    apps = queries.list_for_candidate(db, user)
    out = []
    for a in apps:
        d = app_out(a, "CANDIDATE")
        d["booked_slot"] = next((slot_out(s) for s in queries.active_slots(db, a)), None)
        out.append(d)
    return out


def withdraw(*, app_id: int, user: User, db: Session):
    app = queries.get_for_withdrawal(db, app_id)
    if not app or app.candidate_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn")
    transition_application(db, app, "WITHDRAWN", user.id, "CANDIDATE", note="Ứng viên rút đơn")
    for s in queries.slots_for_withdrawal(db, app):
        s.status, s.held_by, s.held_until, s.application_id = ("OPEN", None, None, None)
    notify(
        db,
        app.job.company.owner_id,
        "APPLICATION",
        f"{user.full_name} đã rút đơn '{app.job.title}'",
        f"/hr/jobs/{app.job_id}",
    )
    db.commit()
    return app_out(app, "CANDIDATE")


def job_applications(*, job_id: int, status: str | None = None, user: User, db: Session):
    job = _own_job(db, user, job_id)
    stmt = queries.for_job(job)
    if status:
        stmt = queries.filter_status(status, stmt)
    apps = queries.list_ranked(db, stmt)
    return {"statuses": APP_STATUSES, "items": [app_out(a, "HR") for a in apps]}


def application_detail(*, app_id: int, user: User, db: Session):
    app = queries.get_detail(db, app_id)
    if not app or app.job.company_id != _company(user).id:
        raise HTTPException(404, "Không tìm thấy đơn")
    d = app_out(app, "HR")
    d["cv"] = cv_out(app.cv, full=True)
    if match := optional_match(app.job, app.cv):
        d["match"] = match
    d["slots"] = [slot_out(s) for s in queries.all_slots(db, app)]
    return d


def transition(*, app_id: int, body: TransitionIn, user: User, db: Session):
    app = queries.get_for_transition(db, app_id)
    if not app or app.job.company_id != _company(user).id:
        raise HTTPException(404, "Không tìm thấy đơn")
    transition_application(db, app, body.to, user.id, "HR", body.note)
    if body.to == "REJECTED":
        for s in queries.slots_for_transition(db, app):
            s.status, s.held_by, s.held_until, s.application_id = ("OPEN", None, None, None)
    audit(db, user, "APP_TRANSITION", "application", app.id, {"to": body.to})
    db.commit()
    db.refresh(app)
    return app_out(app, "HR")
