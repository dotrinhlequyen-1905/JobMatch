from ..core.database import SessionLocal
from ..services.payments import reconcile
from .celery_app import celery_app


@celery_app.task(name="jobmatch.reconcile")
def daily_reconcile():
    with SessionLocal() as db:
        return reconcile(db)
