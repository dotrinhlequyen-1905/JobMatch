"""API quản trị: người dùng, duyệt công ty/tin, gói, giao dịch, đối soát, hoàn tiền, thống kê."""

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import CV, Order, Package, PaymentTransaction, Refund, Report, User
from ..repositories import admin as queries
from ..repositories import payments as payment_queries
from ..schemas.admin import AssignIn, PackageIn, RefundDecision, StatusIn
from ..services.common import audit, company_out, embed_job, iso, job_out, notify, now, order_out, package_out, user_out
from ..services.payments import assign_transaction as payment_assign
from ..services.payments import process_refund, reconcile
from ..services.payments import resolve_order as resolve_reconciling_order
from .auth import revoke_sessions


def stats(*, admin: User, db: Session):

    def count(model, *where):
        return queries.count(db, model, where) or 0

    since = now() - timedelta(days=30)
    revenue = queries.revenue(db) or 0
    daily = queries.daily_revenue(db, since)
    apps_daily = queries.daily_applications(db, since)
    return {
        "users": dict(queries.users_by_role(db)),
        "companies": dict(queries.companies_by_status(db)),
        "jobs": dict(queries.jobs_by_status(db)),
        "applications": dict(queries.applications_by_status(db)),
        "cvs": count(CV),
        "orders": dict(queries.orders_by_status(db)),
        "revenue": int(revenue),
        "revenue_daily": [{"date": str(d), "amount": int(a)} for d, a in daily],
        "applications_daily": [{"date": str(d), "count": c} for d, c in apps_daily],
        "pending_refunds": count(Refund, Refund.status == "REQUESTED"),
        "stray_transactions": count(
            PaymentTransaction, PaymentTransaction.status.not_in(["MATCHED", "RESOLVED"])
        ),
        "reconciling_orders": count(Order, Order.status == "RECONCILING"),
        "open_reports": count(Report, Report.status == "OPEN"),
        "avg_match_score": round(float(queries.avg_match_score(db) or 0), 4),
    }


def users(*, q: str | None = None, role: str | None = None, page: int = 1, size: int = 30, admin: User, db: Session):
    stmt = queries.users()
    if q:
        stmt = queries.filter_user_keyword(q, stmt)
    if role:
        stmt = queries.filter_user_role(role, stmt)
    total = queries.count_users(db, stmt)
    rows = queries.list_users(db, page, size, stmt)
    return {"total": total, "items": [user_out(u) for u in rows]}


def set_user_status(*, user_id: int, body: StatusIn, admin: User, db: Session):
    u = queries.get_user(db, user_id)
    if not u or u.id == admin.id or body.status not in ("ACTIVE", "LOCKED"):
        raise HTTPException(400, "Thao tác không hợp lệ")
    u.status = body.status
    if body.status == "LOCKED":
        # Thu hồi quyền truy cập: access token bị chặn ở bước xác thực, refresh token bị vô hiệu.
        revoke_sessions(db, u)
    audit(db, admin, f"USER_{body.status}", "user", u.id, {"note": body.note})
    db.commit()
    return user_out(u)


def companies(*, status: str | None = "PENDING", page: int = 1, size: int = 30, admin: User, db: Session):
    stmt = queries.companies()
    if status:
        stmt = queries.filter_company_status(status, stmt)
    total = queries.count_companies(db, stmt)
    rows = queries.list_companies(db, page, size, stmt)
    return {"total": total, "items": [company_out(c, with_owner=True) for c in rows]}


def review_company(*, cid: int, body: StatusIn, admin: User, db: Session):
    c = queries.get_company(db, cid)
    if not c or body.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(400, "Thao tác không hợp lệ")
    c.status = body.status
    notify(
        db,
        c.owner_id,
        "MODERATION",
        f"Hồ sơ công ty {('đã được duyệt' if body.status == 'APPROVED' else 'bị từ chối')}"
        + (f": {body.note}" if body.note else ""),
        "/hr/company",
    )
    audit(db, admin, f"COMPANY_{body.status}", "company", c.id, {"note": body.note})
    db.commit()
    return company_out(c, with_owner=True)


def jobs(*, status: str | None = "PENDING", page: int = 1, size: int = 30, admin: User, db: Session):
    stmt = queries.jobs()
    if status:
        stmt = queries.filter_job_status(status, stmt)
    total = queries.count_jobs(db, stmt)
    rows = queries.list_jobs(db, page, size, stmt)
    return {"total": total, "items": [job_out(j) for j in rows]}


def review_job(*, job_id: int, body: StatusIn, admin: User, db: Session):
    j = queries.get_job(db, job_id)
    if not j or body.status not in ("PUBLISHED", "REJECTED"):
        raise HTTPException(400, "Thao tác không hợp lệ")
    if j.status != "PENDING":
        raise HTTPException(409, "Tin không ở trạng thái chờ duyệt")
    j.status = body.status
    if body.status == "PUBLISHED":
        if not j.embedding:
            embed_job(j)
    notify(
        db,
        j.company.owner_id,
        "MODERATION",
        f"Tin '{j.title}' {('đã được duyệt' if body.status == 'PUBLISHED' else 'bị từ chối')}"
        + (f": {body.note}" if body.note else ""),
        "/hr/jobs",
    )
    audit(db, admin, f"JOB_{body.status}", "job", j.id, {"note": body.note})
    db.commit()
    return job_out(j)


def packages(*, admin: User, db: Session):
    return [{**package_out(p), "active": p.active} for p in queries.list_packages(db)]


def upsert_package(*, body: PackageIn, admin: User, db: Session):
    p = queries.find_package(db, body) or Package(code=body.code)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    queries.add_package(db, p)
    audit(db, admin, "PACKAGE_SAVED", "package", None, body.model_dump())
    db.commit()
    return package_out(p)


def orders(*, status: str | None = None, q: str | None = None, page: int = 1, size: int = 30, admin: User, db: Session):
    stmt = queries.orders()
    if status:
        stmt = queries.filter_order_status(status, stmt)
    if q:
        stmt = queries.filter_order_code(q, stmt)
    total = queries.count_orders(db, stmt)
    rows = queries.list_orders(db, page, size, stmt)
    refunds = {r.order_id: r for r in queries.refunds_for_orders(db, rows)}
    return {"total": total, "items": [order_out(o, refunds.get(o.id)) for o in rows]}


def transactions(*, status: str | None = None, page: int = 1, size: int = 30, admin: User, db: Session):
    stmt = queries.transactions()
    if status:
        stmt = queries.filter_transaction_status(status, stmt)
    total = queries.count_transactions(db, stmt)
    rows = queries.list_transactions(db, page, size, stmt)
    return {
        "total": total,
        "items": [
            {
                "id": t.id,
                "sepay_tx_id": t.sepay_tx_id,
                "order_id": t.order_id,
                "amount": t.amount,
                "content": t.content,
                "status": t.status,
                "received_at": iso(t.received_at),
            }
            for t in rows
        ],
    }


def run_reconcile(*, admin: User, db: Session):
    return reconcile(db)


def refunds(*, status: str | None = "REQUESTED", admin: User, db: Session):
    stmt = queries.refunds()
    if status:
        stmt = queries.filter_refund_status(status, stmt)
    return [
        {
            "id": r.id,
            "status": r.status,
            "reason": r.reason,
            "admin_note": r.admin_note,
            "created_at": iso(r.created_at),
            "order": order_out(r.order),
        }
        for r in queries.list_refunds(db, stmt)
    ]


def decide_refund(*, rid: int, body: RefundDecision, admin: User, db: Session):
    r = queries.get_refund(db, rid)
    if not r:
        raise HTTPException(404, "Không tìm thấy yêu cầu")
    process_refund(db, admin, r, body.approve, body.note)
    db.commit()
    return {"ok": True}


def resolve_order(*, order_id: int, body: RefundDecision, admin: User, db: Session):
    order = payment_queries.lock_order_by_id(db, order_id)
    if not order:
        raise HTTPException(404, "Không tìm thấy đơn")
    resolve_reconciling_order(db, admin, order, body.approve, body.note)
    db.commit()
    return order_out(order)


def assign_transaction(*, tx_id: int, body: AssignIn, admin: User, db: Session):
    tx = payment_queries.lock_transaction(db, tx_id)
    order = payment_queries.find_order_by_code(db, body.order_code)
    if not tx or not order:
        raise HTTPException(404, "Không tìm thấy giao dịch hoặc đơn hàng")
    payment_assign(db, admin, tx, order)
    db.commit()
    return order_out(order)


def audit_logs(
    *, action: str | None = None, actor_id: int | None = None, page: int = 1, size: int = 50, admin: User, db: Session
):
    stmt = queries.audit_logs()
    if action:
        stmt = queries.filter_audit_action(action, stmt)
    if actor_id:
        stmt = queries.filter_audit_actor(actor_id, stmt)
    rows = queries.list_audit_logs(db, page, size, stmt)
    return [
        {
            "id": a.id,
            "actor_id": a.actor_id,
            "action": a.action,
            "entity": a.entity,
            "entity_id": a.entity_id,
            "data": a.data,
            "created_at": iso(a.created_at),
        }
        for a in rows
    ]
