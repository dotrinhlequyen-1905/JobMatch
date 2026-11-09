from sqlalchemy import select

from ..core.clock import now
from ..models import AuditLog, Notification, Package, Subscription


def has_active_premium(db, user_id):
    return (
        db.scalar(
            select(Subscription.id)
            .join(Package)
            .where(
                Subscription.user_id == user_id,
                Subscription.active.is_(True),
                Subscription.starts_at <= now(),
                Subscription.ends_at > now(),
                Package.target == "CANDIDATE",
            )
            .limit(1)
        )
        is not None
    )


def add_notification(db, link, title, type_, user_id):
    return db.add(Notification(user_id=user_id, type=type_, title=title, link=link))


def add_audit_log(db, action, actor, data, entity, entity_id):
    return db.add(
        AuditLog(actor_id=actor.id if actor else None, action=action, entity=entity, entity_id=entity_id, data=data)
    )
