from celery import Celery
from celery.schedules import crontab

from ..config import settings

celery_app = Celery(
    "jobmatch",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.embedding_tasks",
        "app.tasks.expiry_tasks",
        "app.tasks.reconciliation_tasks",
        "app.tasks.notification_tasks",
    ],
)
celery_app.conf.update(
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_always_eager=settings.task_always_eager,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "expire-business-records": {"task": "jobmatch.expire", "schedule": 60.0},
        "retry-pending-embeddings": {"task": "jobmatch.pending_embeddings", "schedule": 300.0},
        "interview-reminders": {"task": "jobmatch.interview_reminders", "schedule": 900.0},
        "daily-reconciliation": {"task": "jobmatch.reconcile", "schedule": crontab(hour=0, minute=0)},
    },
)
