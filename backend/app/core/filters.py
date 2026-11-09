from sqlalchemy import or_

from ..models import Job
from .clock import now


def job_is_open():
    return (Job.status == "PUBLISHED") & or_(Job.expires_at.is_(None), Job.expires_at > now())
