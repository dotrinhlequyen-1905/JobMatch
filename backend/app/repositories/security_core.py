from ..models import AuditLog, User


def get_authenticated_user(db, payload):
    return db.get(User, int(payload["sub"]))


def log_denied(db, user, method, path, roles):
    return db.add(
        AuditLog(
            actor_id=user.id,
            action="ACCESS_DENIED",
            entity="endpoint",
            data={"method": method, "path": path, "role": user.role, "required": list(roles)},
        )
    )
