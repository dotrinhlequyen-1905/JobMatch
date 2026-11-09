"""SBERT retrieval -> Cross-Encoder reranking -> skill/experience explanations."""

from ..config import settings
from ..models import CV, Job
from ..repositories.matching import retrieve
from .embedder import cv_profile, from_bytes, get_embedder, jd_profile
from .reranking import score_pairs


def pair_ready(job, cv):
    return bool(
        job.embedding
        and cv.embedding
        and (job.embedding_model == cv.embedding_model == get_embedder().name)
        and (len(job.embedding) == len(cv.embedding))
    )


def skill_gap(jd_skills, cv_skills):
    cv_set = set(cv_skills)
    matched = [skill for skill in jd_skills if skill in cv_set]
    missing = [skill for skill in jd_skills if skill not in cv_set]
    return {
        "matched": matched,
        "missing": missing,
        "extra": [skill for skill in cv_skills if skill not in set(jd_skills)],
        "coverage": round(len(matched) / len(jd_skills), 3) if jd_skills else 0.0,
    }


def exp_match(cv_years, min_years):
    return 1.0 if min_years <= 0 else float(min(1.0, max(0.0, cv_years / min_years)))


def semantic01(cos):
    floor = 0.0 if get_embedder().name == "hashing" else settings.score_cos_floor
    return max(0.0, min(1.0, (cos - floor) / (1 - floor)))


def combine(cos, coverage, exp):
    return round(
        settings.score_w_semantic * semantic01(cos) + settings.score_w_skill * coverage + settings.score_w_exp * exp, 4
    )


def explain(job, cv, cos, cross_score=None):
    gap = skill_gap(job.skills or [], cv.skills or [])
    exp = exp_match(cv.years, job.min_years)
    semantic = semantic01(cos) if cross_score is None else float(cross_score)
    return {
        "score": round(
            settings.score_w_semantic * semantic
            + settings.score_w_skill * gap["coverage"]
            + settings.score_w_exp * exp,
            4,
        ),
        "semantic": round(float(cos), 4),
        "semantic_norm": round(semantic, 4),
        "cross_encoder_score": cross_score,
        "reranking": "cross-encoder" if cross_score is not None else "hybrid",
        "skill_coverage": gap["coverage"],
        "experience_match": round(exp, 3),
        "matched_skills": gap["matched"],
        "missing_skills": gap["missing"],
        "extra_skills": gap["extra"][:10],
        "cv_years": cv.years,
        "required_years": job.min_years,
    }


def _pair(job, cv):
    return (
        cv_profile(cv.title, cv.seniority, cv.years, cv.skills or []),
        jd_profile(job.title, job.role, job.seniority, job.min_years, job.skills or []),
    )


def match_pair(job, cv):
    if not pair_ready(job, cv):
        from fastapi import HTTPException

        raise HTTPException(409, "Embedding cần được xử lý lại bằng cùng một model")
    cosine = float(from_bytes(job.embedding) @ from_bytes(cv.embedding))
    return explain(job, cv, cosine, score_pairs([_pair(job, cv)])[0])


def rank_cvs_for_job(db, job, k=50, candidate_pool=None, rerank_pool=200):
    if not job.embedding or job.embedding_model != get_embedder().name:
        return []
    hits = retrieve(db, CV, from_bytes(job.embedding), max(k, rerank_pool), candidate_pool, get_embedder().name)
    scores = score_pairs([_pair(job, cv) for cv, _ in hits])
    ranked = [(cv, explain(job, cv, cos, cross)) for (cv, cos), cross in zip(hits, scores)]
    return sorted(ranked, key=lambda row: -row[1]["score"])[:k]


def rank_jobs_for_cv(db, cv, k=20, rerank_pool=200):
    if not cv.embedding or cv.embedding_model != get_embedder().name:
        return []
    hits = retrieve(db, Job, from_bytes(cv.embedding), max(k, rerank_pool), None, get_embedder().name)
    scores = score_pairs([_pair(job, cv) for job, _ in hits])
    ranked = [(job, explain(job, cv, cos, cross)) for (job, cos), cross in zip(hits, scores)]
    return sorted(ranked, key=lambda row: -row[1]["score"])[:k]
