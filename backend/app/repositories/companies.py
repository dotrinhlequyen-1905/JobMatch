from sqlalchemy import func, select

from ..core.filters import job_is_open
from ..models import Company, Job


def approved():
    return select(Company).where(Company.status == "APPROVED")


def filter_name(q, stmt):
    return stmt.where(Company.name.ilike(f"%{q}%"))


def count(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def open_job_counts(db):
    return db.execute(select(Job.company_id, func.count()).where(job_is_open()).group_by(Job.company_id)).all()


def list_page(db, page, size, stmt):
    return db.scalars(stmt.order_by(Company.name).offset((page - 1) * size).limit(size)).all()


def get(db, company_id):
    return db.get(Company, company_id)


def add(db, company):
    db.add(company)


def list_open_jobs(db, c):
    return db.scalars(
        select(Job).where(Job.company_id == c.id, job_is_open()).order_by(Job.created_at.desc()).limit(50)
    ).all()
