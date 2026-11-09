from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_admin
from ...models import User
from ...schemas.admin import AssignIn, PackageIn, RefundDecision, StatusIn
from ...schemas.reports import ReportDecision
from ...services import admin as admin_service
from ...services import reports as reports_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def stats(admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.stats(admin=admin, db=db)


@router.get("/users")
def users(
    q: str | None = None,
    role: str | None = None,
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.users(q=q, role=role, page=page, size=size, admin=admin, db=db)


@router.get("/companies")
def companies(
    status: str | None = "PENDING",
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.companies(status=status, page=page, size=size, admin=admin, db=db)


@router.get("/jobs")
def jobs(
    status: str | None = "PENDING",
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.jobs(status=status, page=page, size=size, admin=admin, db=db)


@router.get("/packages")
def packages(admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.packages(admin=admin, db=db)


@router.post("/packages")
def upsert_package(body: PackageIn, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.upsert_package(body=body, admin=admin, db=db)


@router.get("/orders")
def orders(
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.orders(status=status, q=q, page=page, size=size, admin=admin, db=db)


@router.get("/transactions")
def transactions(
    status: str | None = None,
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.transactions(status=status, page=page, size=size, admin=admin, db=db)


@router.get("/reconcile")
def run_reconcile(admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.run_reconcile(admin=admin, db=db)


@router.get("/refunds")
def refunds(status: str | None = "REQUESTED", admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.refunds(status=status, admin=admin, db=db)


@router.post("/orders/{order_id}/resolve")
def resolve_order(order_id: int, body: RefundDecision, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.resolve_order(order_id=order_id, body=body, admin=admin, db=db)


@router.post("/transactions/{tx_id}/assign")
def assign_transaction(tx_id: int, body: AssignIn, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.assign_transaction(tx_id=tx_id, body=body, admin=admin, db=db)


@router.get("/reports")
def reports(
    status: str | None = "OPEN",
    page: int = 1,
    size: int = 30,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return reports_service.admin_list(status=status, page=page, size=size, db=db)


@router.post("/reports/{report_id}")
def decide_report(report_id: int, body: ReportDecision, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return reports_service.decide(report_id=report_id, body=body, admin=admin, db=db)


@router.get("/audit-logs")
def audit_logs(
    action: str | None = None,
    actor_id: int | None = None,
    page: int = 1,
    size: int = 50,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db),
):
    return admin_service.audit_logs(action=action, actor_id=actor_id, page=page, size=size, admin=admin, db=db)


@router.post("/users/{user_id}/status")
def set_user_status(user_id: int, body: StatusIn, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.set_user_status(user_id=user_id, body=body, admin=admin, db=db)


@router.post("/companies/{cid}/review")
def review_company(cid: int, body: StatusIn, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.review_company(cid=cid, body=body, admin=admin, db=db)


@router.patch("/jobs/{job_id}/moderate")
def review_job(job_id: int, body: StatusIn, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.review_job(job_id=job_id, body=body, admin=admin, db=db)


@router.post("/refunds/{rid}")
def decide_refund(rid: int, body: RefundDecision, admin: User = Depends(is_admin), db: Session = Depends(get_db)):
    return admin_service.decide_refund(rid=rid, body=body, admin=admin, db=db)
