from ..core.database import SessionLocal
from ..core.mailer import deliver
from ..services.interviews import send_reminders
from .celery_app import celery_app


@celery_app.task(
    name="jobmatch.send_email", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}
)
def send_email(to, subject, body):
    return deliver(to, subject, body)


@celery_app.task(name="jobmatch.interview_reminders")
def interview_reminders():
    with SessionLocal() as db:
        return send_reminders(db)
