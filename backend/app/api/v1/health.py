from fastapi import APIRouter

from ...config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "ok": True,
        "embedder": settings.embed_model,
        "reranker": settings.cross_encoder_model or "disabled",
        "background": "celery",
    }
