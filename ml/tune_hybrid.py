"""Dò trọng số điểm hybrid trên tập VAL (không dùng test), rồi báo kết quả trên TEST.

score = w_sem * clip((cos - floor) / (1 - floor), 0, 1) + w_skill * độ phủ kỹ năng + w_exp * kinh nghiệm

  python ml/tune_hybrid.py --model models/cvjd-e5-base-profile-clean
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

from ml.evaluate import encode, load_split, metrics, skill_matrix  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def prepare(model, split, text):
    jobs, cvs, qrels = load_split(split)
    key = f"text_{text}"
    prefix = "query: " if "e5" in model.lower() else ""
    cos = encode(model, [j[key] for j in jobs], prefix) @ encode(model, [c[key] for c in cvs], prefix).T
    skill, exp = skill_matrix(jobs, cvs)
    return cos, skill, exp, [j["job_id"] for j in jobs], [c["cv_id"] for c in cvs], qrels


def score(cos, skill, exp, w_sem, w_skill, floor):
    return w_sem * np.clip((cos - floor) / (1 - floor), 0, 1) + w_skill * skill + (1 - w_sem - w_skill) * exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--text", default="profile")
    a = ap.parse_args()
    val = prepare(a.model, "val", a.text)
    best = None
    for w_sem, w_skill, floor in itertools.product(np.arange(0.2, 0.95, 0.1), np.arange(0.05, 0.8, 0.05),
                                                   [0.0, 0.2, 0.3, 0.4, 0.5, 0.6]):
        if w_sem + w_skill > 1.0001:
            continue
        m = metrics(score(*val[:3], w_sem, w_skill, floor), *val[3:])
        if not best or m["ndcg@10"] > best[0]["ndcg@10"]:
            best = (m, round(float(w_sem), 2), round(float(w_skill), 2), floor)
    m, w_sem, w_skill, floor = best
    print(f"VAL tốt nhất: w_sem={w_sem} w_skill={w_skill} w_exp={round(1 - w_sem - w_skill, 2)} floor={floor} -> {m}")
    test = prepare(a.model, "test", a.text)
    t = metrics(score(*test[:3], w_sem, w_skill, floor), *test[3:])
    print(f"TEST với trọng số đó: {t}")
    out = {"model": a.model, "text": a.text, "w_sem": w_sem, "w_skill": w_skill,
           "w_exp": round(1 - w_sem - w_skill, 2), "floor": floor, "val": m, "test": t}
    Path(ROOT / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / f"results/hybrid_{Path(a.model).name}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
