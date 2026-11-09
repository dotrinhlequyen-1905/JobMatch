from sqlalchemy import func, select, update

from ..models import Notification


def list_for_user(db, user):
    return db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)
    ).all()


def count_unread(db, user):
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read.is_(False))
    )


def mark_all_read(db, user):
    return db.execute(update(Notification).where(Notification.user_id == user.id).values(read=True))
