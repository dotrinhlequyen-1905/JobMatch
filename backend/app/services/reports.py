"""Báo cáo vi phạm (FR-8.5, UC-8.6): người dùng gửi, quản trị viên xử lý và lưu lịch sử."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Report, User
from ..repositories import reports as queries
from ..schemas.reports import ReportDecision, ReportIn
from .auth import revoke_sessions
from .common import audit, iso, notify, now


def _target_label(db, r: Report) -> str | None:
    target = queries.get_target(db, r.target_type, r.target_id)
    if target is None:
        return None
    return getattr(target, "title", None) or getattr(target, "name", None) or getattr(target, "full_name", None)


def report_out(db, r: Report, admin=False) -> dict:
    d = {
        "id": r.id,
        "target_type": r.target_type,
        "target_id": r.target_id,
        "target_label": _target_label(db, r),
        "reason": r.reason,
        "status": r.status,
        "admin_note": r.admin_note,
        "created_at": iso(r.created_at),
        "handled_at": iso(r.handled_at),
    }
    if admin:
        d["reporter"] = {"id": r.reporter.id, "email": r.reporter.email, "full_name": r.reporter.full_name}
    return d


def create(*, body: ReportIn, user: User, db: Session):
    target = queries.get_target(db, body.target_type, body.target_id)
    if target is None:
        raise HTTPException(404, "Không tìm thấy đối tượng cần báo cáo")
    if body.target_type == "USER" and target.id == user.id:
        raise HTTPException(400, "Không thể tự báo cáo chính mình")
    if queries.find_open(db, user, body):
        raise HTTPException(409, "Bạn đã gửi báo cáo cho nội dung này và đang chờ xử lý")
    r = Report(reporter_id=user.id, target_type=body.target_type, target_id=body.target_id, reason=body.reason.strip())
    queries.add(db, r)
    db.flush()
    audit(db, user, "REPORT_CREATED", "report", r.id, {"target": f"{body.target_type}#{body.target_id}"})
    db.commit()
    db.refresh(r)
    return report_out(db, r)


def mine(*, user: User, db: Session):
    return [report_out(db, r) for r in queries.list_for_reporter(db, user)]


def admin_list(*, status: str | None = "OPEN", page: int = 1, size: int = 30, db: Session):
    stmt = queries.reports(status)
    total = queries.count(db, stmt)
    return {"total": total, "items": [report_out(db, r, admin=True) for r in queries.list_page(db, page, size, stmt)]}


def decide(*, report_id: int, body: ReportDecision, admin: User, db: Session):
    r = queries.lock(db, report_id)
    if not r:
        raise HTTPException(404, "Không tìm thấy báo cáo")
    if r.status != "OPEN":
        raise HTTPException(409, "Báo cáo đã được xử lý")
    if body.action != "NONE" and body.status != "RESOLVED":
        raise HTTPException(400, "Chỉ áp dụng biện pháp khi xác nhận vi phạm")
    if body.action == "CLOSE_JOB":
        if r.target_type != "JOB":
            raise HTTPException(400, "Biện pháp đóng tin chỉ áp dụng cho báo cáo tin tuyển dụng")
        job = queries.get_target(db, "JOB", r.target_id)
        job.status = "CLOSED"
        notify(db, job.company.owner_id, "MODERATION", f"Tin '{job.title}' bị đóng do vi phạm", "/hr/jobs")
    elif body.action == "LOCK_USER":
        owner = queries.owner_of(db, r)
        if owner is None or owner.role == "ADMIN":
            raise HTTPException(400, "Không thể khóa tài khoản này")
        owner.status = "LOCKED"
        revoke_sessions(db, owner)
    r.status, r.admin_note, r.handled_by, r.handled_at = (body.status, body.note, admin.id, now())
    notify(
        db,
        r.reporter_id,
        "REPORT",
        "Báo cáo vi phạm của bạn đã được xử lý" if body.status == "RESOLVED" else "Báo cáo của bạn đã được xem xét",
        None,
    )
    audit(db, admin, f"REPORT_{body.status}", "report", r.id, {"action": body.action, "note": body.note})
    db.commit()
    return report_out(db, r, admin=True)
