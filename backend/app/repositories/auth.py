from sqlalchemy import select, update

from ..core.clock import now
from ..models import AuthToken, Company, User


def find_registered_email(db, body):
    return db.scalar(select(User).where(User.email == body.email.lower()))


def add_user(db, user):
    return db.add(user)


def add_company(db, body, user):
    return db.add(Company(owner_id=user.id, name=body.company_name.strip()))


def find_login_email(db, body):
    return db.scalar(select(User).where(User.email == body.email.lower()))


def find_user_by_email(db, email):
    return db.scalar(select(User).where(User.email == email.lower()))


def add_token(db, token):
    return db.add(token)


def lock_token(db, token_hash, purpose):
    return db.scalar(
        select(AuthToken).where(AuthToken.token_hash == token_hash, AuthToken.purpose == purpose).with_for_update()
    )


def revoke_tokens(db, user_id, purpose):
    return db.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user_id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None))
        .values(used_at=now())
    )
