import numpy as np
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import cast, func, select

from ..config import settings
from ..core.filters import job_is_open
from ..models import CV, Application, CandidateProfile, Job, Notification


def applied_job_ids(db, user):
    return db.scalars(select(Application.job_id).where(Application.candidate_id == user.id))


def get_job(db, job_id):
    return db.get(Job, job_id)


def applied_candidate_ids(db, job):
    return db.scalars(select(Application.candidate_id).where(Application.job_id == job.id))


def invited_candidate_ids(db, job):
    return db.scalars(
        select(Notification.user_id).where(Notification.type == "INVITE", Notification.link == f"/jobs/{job.id}")
    )


def retrieve(db, model, query, limit, allowed=None, embedding_model=None):
    filters = [model.embedding.is_not(None), model.embedding_model == (embedding_model or settings.embed_model)]
    if model is Job:
        filters.append(job_is_open())
    else:
        hidden = select(CandidateProfile.user_id).where(CandidateProfile.is_public.is_(False))
        filters.extend([CV.candidate.has(status="ACTIVE"), CV.is_default.is_(True), CV.candidate_id.not_in(hidden)])
    if allowed is not None:
        filters.append(model.id.in_(allowed))
    if db.bind.dialect.name == "postgresql":
        filters.append(func.vector_dims(model.embedding) == len(query))
        distance = cast(model.embedding, VECTOR(len(query))).cosine_distance(query.tolist())
        rows = db.execute(
            select(model, distance.label("distance")).where(*filters).order_by(distance).limit(limit)
        ).all()
        return [(entity, 1.0 - float(value)) for entity, value in rows]
    rows = db.scalars(select(model).where(*filters)).all()
    scored = []
    for entity in rows:
        vector = np.frombuffer(entity.embedding, dtype=np.float32)
        if len(vector) == len(query):
            scored.append((entity, float(vector @ query)))
    return sorted(scored, key=lambda row: -row[1])[:limit]


def applied_with_cv(db, job, cv_id):
    return db.scalar(select(Application.id).where(Application.job_id == job.id, Application.cv_id == cv_id).limit(1))


def get_cv(db, cv_id):
    return db.get(CV, cv_id)
