from ..ai.embedder import get_embedder, to_bytes
from ..core.database import SessionLocal
from ..models import CV, Job
from ..repositories import embedding_tasks as queries
from ..services.common import cv_text, job_text
from .celery_app import celery_app


@celery_app.task(
    name="jobmatch.embedding", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}
)
def build_embedding(kind, entity_id, revision):
    model, text_fn = (CV, cv_text) if kind == "cv" else (Job, job_text)
    with SessionLocal() as db:
        entity = queries.get(db, entity_id, model)
        if entity is None or entity.embedding_revision != revision:
            return "obsolete"
        vector = to_bytes(get_embedder().encode([text_fn(entity)])[0])
        db.refresh(entity, with_for_update=True)
        if entity.embedding_revision != revision:
            return "obsolete"
        entity.embedding, entity.processing_status = (vector, "READY")
        entity.embedding_model = get_embedder().name
        db.commit()
    return "ready"


@celery_app.task(name="jobmatch.pending_embeddings")
def pending_embeddings():
    with SessionLocal() as db:
        for kind, model in (("cv", CV), ("job", Job)):
            for entity_id, revision in queries.pending(db, model):
                build_embedding.delay(kind, entity_id, revision)
