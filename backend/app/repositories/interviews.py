from sqlalchemy import and_, or_, select, update

from ..core.clock import now
from ..models import Application, InterviewSlot, User


def application_for_slots(db, app_id):
    return db.get(Application, app_id)


def available_for_application(db, app):
    return db.scalars(
        select(InterviewSlot)
        .where(
            InterviewSlot.job_id == app.job_id,
            InterviewSlot.start_at > now(),
            InterviewSlot.status.in_(["OPEN", "HELD"]),
        )
        .order_by(InterviewSlot.start_at)
    ).all()


def list_for_job(db, job):
    return db.scalars(
        select(InterviewSlot).where(InterviewSlot.job_id == job.id).order_by(InterviewSlot.start_at)
    ).all()


def applications_for_job(db, job):
    return db.scalars(select(Application).where(Application.job_id == job.id))


def get_for_cancel(db, slot_id):
    return db.get(InterviewSlot, slot_id)


def get_for_result(db, slot_id):
    return db.get(InterviewSlot, slot_id)


def find_overlap(db, end, hr, start):
    return db.scalar(
        select(InterviewSlot.id)
        .where(
            InterviewSlot.hr_id == hr.id,
            InterviewSlot.status != "CANCELLED",
            InterviewSlot.start_at < end,
            InterviewSlot.end_at > start,
        )
        .limit(1)
    )


def find_candidate_overlap(db, app, slot):
    """Lịch khác của cùng ứng viên (đã đặt hoặc đang giữ còn hạn) chồng giờ với `slot`."""
    return db.scalar(
        select(InterviewSlot.id)
        .join(Application, Application.id == InterviewSlot.application_id)
        .where(
            Application.candidate_id == app.candidate_id,
            InterviewSlot.application_id != app.id,
            or_(
                InterviewSlot.status == "BOOKED",
                and_(InterviewSlot.status == "HELD", InterviewSlot.held_until >= now()),
            ),
            InterviewSlot.start_at < slot.end_at,
            InterviewSlot.end_at > slot.start_at,
        )
        .limit(1)
    )


def add_all(db, out):
    return db.add_all(out)


def get_candidate_application(db, application_id):
    return db.get(Application, application_id)


def get_for_hold(db, slot_id):
    return db.get(InterviewSlot, slot_id)


def release_previous_hold(db, app):
    return db.execute(
        update(InterviewSlot)
        .where(InterviewSlot.application_id == app.id, InterviewSlot.status == "HELD")
        .values(status="OPEN", held_by=None, held_until=None, application_id=None)
        .execution_options(synchronize_session=False)
    )


def build_hold(app, interval, slot_id, user):
    return (
        update(InterviewSlot)
        .where(
            InterviewSlot.id == slot_id,
            or_(InterviewSlot.status == "OPEN", and_(InterviewSlot.status == "HELD", InterviewSlot.held_until < now())),
        )
        .values(status="HELD", held_by=user.id, application_id=app.id, held_until=now() + interval)
        .returning(InterviewSlot.id)
        .execution_options(synchronize_session=False)
    )


def execute_hold(db, stmt):
    return db.execute(stmt).scalar()


def build_confirmation(slot_id, user):
    return (
        update(InterviewSlot)
        .where(
            InterviewSlot.id == slot_id,
            InterviewSlot.status == "HELD",
            InterviewSlot.held_by == user.id,
            InterviewSlot.held_until >= now(),
        )
        .values(status="BOOKED", held_until=None)
        .returning(InterviewSlot.application_id)
        .execution_options(synchronize_session=False)
    )


def execute_confirmation(db, stmt):
    return db.execute(stmt).scalar()


def application_for_confirmation(db, app_id):
    return db.get(Application, app_id)


def slot_for_confirmation(db, slot_id):
    return db.get(InterviewSlot, slot_id)


def release_expired(db):
    return db.execute(
        update(InterviewSlot)
        .where(InterviewSlot.status == "HELD", InterviewSlot.held_until < now())
        .values(status="OPEN", held_by=None, held_until=None, application_id=None)
        .execution_options(synchronize_session=False)
    )


def application_for_cancellation(db, slot):
    return db.get(Application, slot.application_id)


def application_for_result(db, slot):
    return db.get(Application, slot.application_id)


def lock_slot(db, slot_id):
    return db.get(InterviewSlot, slot_id, with_for_update=True)


def due_reminders(db, until):
    return db.scalars(
        select(InterviewSlot.id).where(
            InterviewSlot.status == "BOOKED",
            InterviewSlot.reminder_sent_at.is_(None),
            InterviewSlot.start_at > now(),
            InterviewSlot.start_at <= until,
        )
    ).all()


def claim_reminder(db, slot_id):
    """Đánh dấu đã nhắc bằng UPDATE có điều kiện để hai worker không gửi trùng."""
    return db.execute(
        update(InterviewSlot)
        .where(InterviewSlot.id == slot_id, InterviewSlot.reminder_sent_at.is_(None))
        .values(reminder_sent_at=now())
        .execution_options(synchronize_session=False)
    )


def get_slot(db, slot_id):
    return db.get(InterviewSlot, slot_id)


def get_user(db, user_id):
    return db.get(User, user_id)
