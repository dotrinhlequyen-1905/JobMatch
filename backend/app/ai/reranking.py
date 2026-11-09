"""Evaluate retrieved CV/JD pairs with a lazily loaded Cross-Encoder."""

import threading
from functools import lru_cache

import numpy as np

from ..config import ROOT_DIR, settings

_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_cross_encoder():
    if not settings.cross_encoder_model:
        return None
    import torch
    from sentence_transformers import CrossEncoder

    local = ROOT_DIR / settings.cross_encoder_model
    # Giống embedder: EMBED_DEVICE=cuda nhưng máy/container không có GPU thì chạy CPU.
    device = settings.embed_device if settings.embed_device != "cuda" or torch.cuda.is_available() else "cpu"
    return CrossEncoder(str(local) if local.exists() else settings.cross_encoder_model, device=device)


def score_pairs(pairs):
    model = get_cross_encoder()
    if model is None:
        return [None] * len(pairs)
    if not pairs:
        return []
    with _lock:
        logits = np.asarray(
            model.predict(pairs, batch_size=16, show_progress_bar=False, activation_fn=lambda values: values),
            dtype=np.float32,
        ).reshape(-1)
    return (1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))).tolist()
