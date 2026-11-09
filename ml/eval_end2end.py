"""Đánh giá ĐẦU-CUỐI giống hệ thống thật trên CV do LLM viết lại (test_llm):
văn bản CV -> bộ trích xuất (backend/app/ai/cv_parser.py) -> profile -> model -> xếp hạng.
Nhãn đúng (qrels) vẫn tính từ dữ liệu gốc; chỉ phần đầu vào của hệ thống là văn bản tự do.

  python ml/eval_end2end.py --methods bm25 e5-base e5-base+hybrid models/cvjd-e5-base-profile-clean+hybrid
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
from ml.evaluate import bm25_scores, encode, metrics  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=["bm25", "skill", "e5-base", "e5-base+hybrid",
                                                     "models/cvjd-e5-base-profile-clean",
                                                     "models/cvjd-e5-base-profile-clean+hybrid"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import os
    os.environ.setdefault("EMBED_MODEL", "hashing")    # chỉ dùng parser + hàm profile của backend
    from app.ai.cv_parser import parse_cv_text
    from app.ai.embedder import cv_profile

    jobs = {j["job_id"]: j for j in map(json.loads, open(ROOT / "data/final/jobs.jsonl", encoding="utf-8"))}
    cvs = {c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final/cvs_llm.jsonl", encoding="utf-8"))}
    ir = json.load(open(ROOT / "data/final/test_llm_ir.json", encoding="utf-8"))
    qids, cids = ir["queries"], ir["corpus"]
    parsed, skill_hit = {}, []
    for cid in cids:
        p = parse_cv_text(cvs[cid]["text"])
        parsed[cid] = p
        gold = set(cvs[cid]["skills"])
        skill_hit.append((len(gold & set(p["skills"])), len(set(p["skills"])), len(gold)))
    tp, npred, ngold = map(sum, zip(*skill_hit))
    print(f"Trích xuất trên {len(cids)} CV viết lại: precision kỹ năng {tp / npred:.3f}, recall {tp / ngold:.3f}; "
          f"số năm đúng {np.mean([parsed[c]['years'] == cvs[c]['years'] for c in cids]):.1%}")

    q_text = [jobs[q]["text_profile"] for q in qids]
    c_text = [cv_profile(parsed[c]["title"] or "Ứng viên", parsed[c]["seniority"], parsed[c]["years"],
                         parsed[c]["skills"], parsed[c]["experience"], parsed[c]["major"]) for c in cids]
    skill = np.zeros((len(qids), len(cids)), dtype=np.float32)
    exp = np.zeros_like(skill)
    for i, q in enumerate(qids):
        js = set(jobs[q]["skills"])
        for k, c in enumerate(cids):
            skill[i, k] = len(js & set(parsed[c]["skills"])) / len(js)
            my = jobs[q]["min_years"]
            exp[i, k] = 1.0 if my <= 0 else min(1.0, parsed[c]["years"] / my)

    results, cache = {}, {}
    for m in a.methods:
        base, hybrid = m.split("+")[0], m.endswith("+hybrid")
        if base == "bm25":
            sc = bm25_scores(q_text, [cvs[c]["text"] for c in cids])   # BM25 trên toàn văn CV
        elif base == "skill":
            sc = skill + 0.01 * exp
        else:
            if base not in cache:
                prefix = "query: " if "e5" in base.lower() else ""
                cache[base] = encode(base, q_text, prefix) @ encode(base, c_text, prefix).T
            sc = cache[base]
            if hybrid:   # trọng số dò trên val (ml/tune_hybrid.py)
                w = json.load(open(ROOT / f"results/hybrid_{Path(base).name}.json"))
                sc = (w["w_sem"] * np.clip((sc - w["floor"]) / (1 - w["floor"]), 0, 1) + w["w_skill"] * skill
                      + w["w_exp"] * exp)
        results[m] = metrics(sc, qids, cids, ir["qrels"])
        print(f"{m:45} {results[m]}", flush=True)
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
