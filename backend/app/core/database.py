import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import settings

engine_options = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update(pool_size=10, max_overflow=20)
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


@event.listens_for(SessionLocal, "after_flush")
def sync_skill_index(session, context):
    from .skill_index import after_flush

    after_flush(session, context)


@event.listens_for(SessionLocal, "after_commit")
def dispatch_embeddings(session):
    from ..tasks.embedding_tasks import build_embedding

    for payload in session.info.pop("embedding_tasks", []):
        try:
            build_embedding.delay(*payload)
        except Exception:
            logging.getLogger(__name__).exception("Embedding dispatch failed; pending row retained")


@event.listens_for(SessionLocal, "after_commit")
def dispatch_emails(session):
    from ..tasks.notification_tasks import send_email

    for payload in session.info.pop("email_tasks", []):
        try:
            send_email.delay(*payload)
        except Exception:
            logging.getLogger(__name__).exception("Email dispatch failed")


@event.listens_for(SessionLocal, "after_rollback")
def discard_embeddings(session):
    session.info.pop("embedding_tasks", None)
    session.info.pop("email_tasks", None)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
