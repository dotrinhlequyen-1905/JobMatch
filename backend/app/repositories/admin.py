from sqlalchemy import func, or_, select

from ..models import Application, AuditLog, Company, Job, Order, Package, PaymentTransaction, Refund, User


def count(db, model, where):
    return db.scalar(select(func.count()).select_from(model).where(*where))


def revenue(db):
    return db.scalar(select(func.coalesce(func.sum(Order.amount), 0)).where(Order.status == "PAID"))


def daily_revenue(db, since):
    return db.execute(
        select(func.date(Order.paid_at), func.sum(Order.amount))
        .where(Order.status == "PAID", Order.paid_at >= since)
        .group_by(func.date(Order.paid_at))
        .order_by(func.date(Order.paid_at))
    ).all()


def daily_applications(db, since):
    return db.execute(
        select(func.date(Application.created_at), func.count())
        .where(Application.created_at >= since)
        .group_by(func.date(Application.created_at))
        .order_by(func.date(Application.created_at))
    ).all()


def users_by_role(db):
    return db.execute(select(User.role, func.count()).group_by(User.role)).all()


def companies_by_status(db):
    return db.execute(select(Company.status, func.count()).group_by(Company.status)).all()


def jobs_by_status(db):
    return db.execute(select(Job.status, func.count()).group_by(Job.status)).all()


def applications_by_status(db):
    return db.execute(select(Application.status, func.count()).group_by(Application.status)).all()


def orders_by_status(db):
    return db.execute(select(Order.status, func.count()).group_by(Order.status)).all()


def users():
    return select(User)


def filter_user_keyword(q, stmt):
    return stmt.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))


def filter_user_role(role, stmt):
    return stmt.where(User.role == role)


def count_users(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_users(db, page, size, stmt):
    return db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()


def get_user(db, user_id):
    return db.get(User, user_id)


def companies():
    return select(Company)


def filter_company_status(status, stmt):
    return stmt.where(Company.status == status)


def count_companies(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_companies(db, page, size, stmt):
    return db.scalars(stmt.order_by(Company.id.desc()).offset((page - 1) * size).limit(size)).all()


def get_company(db, cid):
    return db.get(Company, cid)


def jobs():
    return select(Job)


def filter_job_status(status, stmt):
    return stmt.where(Job.status == status)


def count_jobs(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_jobs(db, page, size, stmt):
    return db.scalars(stmt.order_by(Job.id.desc()).offset((page - 1) * size).limit(size)).all()


def get_job(db, job_id):
    return db.get(Job, job_id)


def list_packages(db):
    return db.scalars(select(Package).order_by(Package.id))


def find_package(db, body):
    return db.scalar(select(Package).where(Package.code == body.code))


def add_package(db, p):
    return db.add(p)


def orders():
    return select(Order)


def filter_order_status(status, stmt):
    return stmt.where(Order.status == status)


def filter_order_code(q, stmt):
    return stmt.where(Order.order_code.ilike(f"%{q}%"))


def count_orders(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_orders(db, page, size, stmt):
    return db.scalars(stmt.order_by(Order.id.desc()).offset((page - 1) * size).limit(size)).all()


def refunds_for_orders(db, rows):
    return db.scalars(select(Refund).where(Refund.order_id.in_([o.id for o in rows])))


def transactions():
    return select(PaymentTransaction)


def filter_transaction_status(status, stmt):
    return stmt.where(PaymentTransaction.status == status)


def count_transactions(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_transactions(db, page, size, stmt):
    return db.scalars(stmt.order_by(PaymentTransaction.id.desc()).offset((page - 1) * size).limit(size)).all()


def refunds():
    return select(Refund)


def filter_refund_status(status, stmt):
    return stmt.where(Refund.status == status)


def list_refunds(db, stmt):
    return db.scalars(stmt.order_by(Refund.id.desc()))


def get_refund(db, rid):
    return db.get(Refund, rid)


def audit_logs():
    return select(AuditLog)


def filter_audit_action(action, stmt):
    return stmt.where(AuditLog.action.ilike(f"%{action}%"))


def filter_audit_actor(actor_id, stmt):
    return stmt.where(AuditLog.actor_id == actor_id)


def list_audit_logs(db, page, size, stmt):
    return db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)).all()


def avg_match_score(db):
    return db.scalar(select(func.avg(Application.match_score)).where(Application.match_score.is_not(None)))
