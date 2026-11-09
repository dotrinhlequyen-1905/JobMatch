from ..core.database import SessionLocal
from ..services.expiry import close_expired_jobs
from ..services.interviews import release_expired
from ..services.payments import expire_orders
from .celery_app import celery_app


@celery_app.task(name="jobmatch.expire")
def expire_records():
    with SessionLocal() as db:
        return {"slots": release_expired(db), "orders": expire_orders(db), "jobs": close_expired_jobs(db)}
