from sqlalchemy import select, update

from ..models import CV, Application, Job


def get(db, cv_id):
    return db.get(CV, cv_id)


def default_for_candidate(db, user):
    return db.scalar(select(CV).where(CV.candidate_id == user.id).order_by(CV.is_default.desc(), CV.id.desc()))


def list_for_candidate(db, user):
    return db.scalars(select(CV).where(CV.candidate_id == user.id).order_by(CV.id.desc()))


def has_cv(db, user):
    return db.scalar(select(CV.id).where(CV.candidate_id == user.id).limit(1))


def add(db, cv):
    return db.add(cv)


def clear_default(db, user):
    return db.execute(update(CV).where(CV.candidate_id == user.id).values(is_default=False))


def is_used(db, cv):
    return db.scalar(select(Application.id).where(Application.cv_id == cv.id).limit(1))


def delete(db, cv):
    return db.delete(cv)


def get_for_download(db, cv_id):
    return db.get(CV, cv_id)


def hr_can_access(db, cv, user):
    return db.scalar(
        select(Application.id)
        .join(Job)
        .where(Application.cv_id == cv.id, Job.company_id == (user.company.id if user.company else -1))
    )
