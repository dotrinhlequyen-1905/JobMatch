"""Đánh giá xếp hạng CV cho JD (và JD cho CV) trên tập val/test.

  python ml/evaluate.py --split test --methods bm25 hybrid e5-base
  python ml/evaluate.py --split test --methods models/cvjd-e5 --text profile

Phương pháp:
  bm25                 : lọc từ khóa truyền thống (baseline)
  skill                : chỉ độ phủ kỹ năng (sau chuẩn hóa)
  <tên/đường dẫn model>: bi-encoder (sentence-transformers), cosine
  thêm hậu tố "+hybrid" (vd e5-base+hybrid): điểm tổng như web = 0.6 cos + 0.3 kỹ năng + 0.1 kinh nghiệm
Chỉ số: NDCG@10, MRR@10, Recall@20, Recall@50 (qrels graded 1/2).
"""
import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {"e5-base": "intfloat/multilingual-e5-base", "e5-small": "intfloat/multilingual-e5-small",
           "e5-large": "intfloat/multilingual-e5-large", "bkai": "bkai-foundation-models/vietnamese-bi-encoder",
           "mpnet": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"}


def load_split(split):
    jobs = {j["job_id"]: j for j in map(json.loads, open(ROOT / "data/final/jobs.jsonl", encoding="utf-8"))}
    cvs = {c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final/cvs.jsonl", encoding="utf-8"))}
    ir = json.load(open(ROOT / f"data/final/{split}_ir.json", encoding="utf-8"))
    if ir.get("cv_source"):   # tập *_llm: dùng CV đã được LLM viết lại
        cvs.update({c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final" / ir["cv_source"], encoding="utf-8"))})
    return [jobs[q] for q in ir["queries"]], [cvs[c] for c in ir["corpus"]], ir["qrels"]


def metrics(scores: np.ndarray, qids, cids, qrels):
    out = {"ndcg@10": [], "mrr@10": [], "recall@20": [], "recall@50": []}
    for i, q in enumerate(qids):
        rel = qrels.get(q, {})
        if not rel:
            continue
        order = np.argsort(-scores[i])
        ranked = [cids[j] for j in order[:50]]
        dcg = sum((2 ** rel.get(c, 0) - 1) / math.log2(k + 2) for k, c in enumerate(ranked[:10]))
        ideal = sorted(rel.values(), reverse=True)[:10]
        idcg = sum((2 ** r - 1) / math.log2(k + 2) for k, r in enumerate(ideal))
        out["ndcg@10"].append(dcg / idcg)
        out["mrr@10"].append(next((1 / (k + 1) for k, c in enumerate(ranked[:10]) if rel.get(c, 0) == 2), 0.0))
        strong = {c for c, r in rel.items() if r == 2} or set(rel)
        out["recall@20"].append(len(strong & set(ranked[:20])) / len(strong))
        out["recall@50"].append(len(strong & set(ranked[:50])) / len(strong))
    return {k: round(float(np.mean(v)), 4) for k, v in out.items()}


def tok(s):
    return re.findall(r"[\w.#+/]+", s.lower())


def bm25_scores(q_texts, c_texts):
    from rank_bm25 import BM25Okapi
    bm = BM25Okapi([tok(t) for t in c_texts])
    return np.stack([bm.get_scores(tok(q)) for q in q_texts])


def skill_matrix(jobs, cvs):
    s = np.zeros((len(jobs), len(cvs)), dtype=np.float32)
    e = np.zeros_like(s)
    for i, j in enumerate(jobs):
        js = set(j["skills"])
        for k, c in enumerate(cvs):
            s[i, k] = len(js & set(c["skills"])) / len(js)
            e[i, k] = 1.0 if j["min_years"] <= 0 else min(1.0, c["years"] / j["min_years"])
    return s, e


def encode(model_name, texts, prefix, batch_size=32):
    from sentence_transformers import SentenceTransformer
    path = ROOT / model_name
    model = SentenceTransformer(str(path) if path.exists() else ALIASES.get(model_name, model_name), device="cuda")
    model.max_seq_length = min(model.max_seq_length or 512, 512)
    return model.encode([prefix + t for t in texts], batch_size=batch_size, normalize_embeddings=True,
                        show_progress_bar=False, convert_to_numpy=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--methods", nargs="+", default=["bm25", "skill", "e5-base", "e5-base+hybrid"])
    ap.add_argument("--text", default="profile", choices=["profile", "full"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    jobs, cvs, qrels = load_split(a.split)
    qids, cids = [j["job_id"] for j in jobs], [c["cv_id"] for c in cvs]
    key = f"text_{a.text}"
    skill, exp = skill_matrix(jobs, cvs)
    results = {}
    cache = {}
    print(f"[{a.split}] {len(jobs)} JD x {len(cvs)} CV, text={a.text}")
    for m in a.methods:
        t0 = time.time()
        base, hybrid = m.split("+")[0], m.endswith("+hybrid")
        if base == "bm25":
            sc = bm25_scores([j[key] for j in jobs], [c[key] for c in cvs])
        elif base == "skill":
            sc = skill + 0.01 * exp
        else:
            if base not in cache:
                prefix = "query: " if "e5" in base.lower() else ""
                q = encode(base, [j[key] for j in jobs], prefix)
                c = encode(base, [c[key] for c in cvs], prefix)
                cache[base] = q @ c.T
            sc = cache[base]
            if hybrid:
                sc = 0.6 * np.clip((sc - 0.5) / 0.5, 0, 1) + 0.3 * skill + 0.1 * exp
        r = metrics(sc, qids, cids, qrels)
        # chiều ngược: CV -> JD (gợi ý việc làm cho ứng viên)
        rev_qrels = {}
        for q, rel in qrels.items():
            for c, v in rel.items():
                rev_qrels.setdefault(c, {})[q] = v
        r_rev = metrics(sc.T, cids, qids, rev_qrels)
        results[m] = {"jd2cv": r, "cv2jd": r_rev, "sec": round(time.time() - t0, 1)}
        print(f"{m:40} JD→CV {r} | CV→JD ndcg@10={r_rev['ndcg@10']} ({results[m]['sec']}s)", flush=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"split": a.split, "text": a.text, "results": results}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
