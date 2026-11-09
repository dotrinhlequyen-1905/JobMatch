from sqlalchemy import update

from ..core.clock import now
from ..models import Job


def close_expired_jobs(db):
    return db.execute(update(Job).where(Job.status == "PUBLISHED", Job.expires_at < now()).values(status="CLOSED"))
