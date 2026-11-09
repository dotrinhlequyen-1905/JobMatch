from sqlalchemy.orm import Session

from ..models import User
from ..repositories import notifications as queries
from ..services.common import iso


def list_notifications(*, user: User, db: Session):
    rows = queries.list_for_user(db, user)
    unread = queries.count_unread(db, user)
    return {
        "unread": unread,
        "items": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "link": n.link,
                "read": n.read,
                "created_at": iso(n.created_at),
            }
            for n in rows
        ],
    }


def read_all(*, user: User, db: Session):
    queries.mark_all_read(db, user)
    db.commit()
    return {"ok": True}
