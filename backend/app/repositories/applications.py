from sqlalchemy import select

from ..models import Application, ApplicationHistory, InterviewSlot, Job


def job_for_application(db, body):
    return db.get(Job, body.job_id)


def add(db, app):
    return db.add(app)


def add_initial_history(db, app, user):
    return db.add(ApplicationHistory(application_id=app.id, from_status=None, to_status="NEW", actor_id=user.id))


def list_for_candidate(db, user):
    return db.scalars(
        select(Application).where(Application.candidate_id == user.id).order_by(Application.updated_at.desc())
    ).all()


def active_slots(db, a):
    return db.scalars(
        select(InterviewSlot).where(InterviewSlot.application_id == a.id, InterviewSlot.status.in_(["HELD", "BOOKED"]))
    )


def get_for_withdrawal(db, app_id):
    return db.get(Application, app_id)


def slots_for_withdrawal(db, app):
    return db.scalars(
        select(InterviewSlot).where(
            InterviewSlot.application_id == app.id, InterviewSlot.status.in_(["HELD", "BOOKED"])
        )
    )


def for_job(job):
    return select(Application).where(Application.job_id == job.id)


def filter_status(status, stmt):
    return stmt.where(Application.status == status)


def list_ranked(db, stmt):
    return db.scalars(stmt.order_by(Application.match_score.desc().nulls_last())).all()


def get_detail(db, app_id):
    return db.get(Application, app_id)


def all_slots(db, app):
    return db.scalars(select(InterviewSlot).where(InterviewSlot.application_id == app.id))


def get_for_transition(db, app_id):
    return db.get(Application, app_id)


def slots_for_transition(db, app):
    return db.scalars(
        select(InterviewSlot).where(
            InterviewSlot.application_id == app.id, InterviewSlot.status.in_(["HELD", "BOOKED"])
        )
    )
