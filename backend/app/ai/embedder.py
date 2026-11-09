"""Sinh vector embedding cho JD/CV.

- Mặc định dùng sentence-transformers (model pretrained hoặc model đã fine-tune trong thư mục models/).
- "hashing" chỉ dùng cho kiểm thử hoặc khi cấu hình cho phép dự phòng rõ ràng.
"""

import hashlib
import logging
import re
import threading

import numpy as np
from data_pipeline import profile_text as P

from ..config import ROOT_DIR, settings

log = logging.getLogger(__name__)


def jd_profile(title, role, seniority, min_years, skills) -> str:
    return P.jd_profile(
        {
            "title": title,
            "role": role if role in P.ROLE_DISPLAY else "software_engineer",
            "seniority": seniority if seniority in P.SENIORITY_VI else "junior",
            "min_years": min_years,
            "skills": skills,
        }
    )


def cv_profile(title, seniority, years, skills, experience=(), major="") -> str:
    """experience: [{position, start, end}] ; major: ngành học — cùng định dạng dữ liệu train."""
    return P.cv_profile(
        {
            "title": title,
            "seniority": seniority if seniority in P.SENIORITY_VI else "junior",
            "years": years,
            "skills": skills,
            "experience": [
                {"position": e.get("position", ""), "start": e.get("start", ""), "end": e.get("end")}
                for e in experience
            ],
            "education": {"major": major or "—"},
        }
    )


class HashingEmbedder:
    dim = 1024

    def encode(self, texts, **_):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in re.findall("[\\w.#+/]+", t.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1 if h >> 64 & 1 else -1
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-09)


class Embedder:
    def __init__(self, name: str, device: str):
        self.name = name
        self._lock = threading.Lock()
        self.prefix = "query: " if "e5" in name.lower() else ""
        if name == "hashing":
            self.model = HashingEmbedder()
            return
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            local = ROOT_DIR / name
            dev = device if device != "cuda" or torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer(str(local) if local.exists() else name, device=dev)
            log.info("Embedding model: %s trên %s", name, dev)
        except Exception as e:
            if not settings.allow_hashing_fallback:
                raise RuntimeError(f"Không nạp được model embedding {name}") from e
            log.warning("Không nạp được model %s (%s) -> dùng hashing", name, e)
            self.name, self.prefix, self.model = ("hashing", "", HashingEmbedder())

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        with self._lock:
            vecs = self.model.encode(
                [self.prefix + t for t in texts],
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 500,
            )
        return np.asarray(vecs, dtype=np.float32)


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder(settings.embed_model, settings.embed_device)
    return _embedder


def to_bytes(v: np.ndarray) -> bytes:
    return v.astype(np.float32).tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)
