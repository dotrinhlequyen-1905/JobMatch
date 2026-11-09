"""Đánh giá xếp hạng bằng nhãn LLM (độc lập với luật chấm theo kỹ năng).

Tập: 50 JD của file gán nhãn tay, mỗi JD 10 CV, nhãn 0/1/2 do Nemotron-3-Ultra chấm (data/llm/label_reviews.jsonl,
source=annotation). Mỗi phương pháp xếp hạng 10 CV trong từng JD -> NDCG@10, P@3 (tỉ lệ nhãn>=1 trong top 3),
độ chính xác cặp (cặp CV khác nhãn có được xếp đúng thứ tự không).

  python ml/eval_llm_labels.py --methods bm25 skill e5-base e5-base+hybrid models/cvjd-e5-base-profile
  thêm --human để dùng nhãn chấm tay trong data/annotation/annotate_test.xlsx (khi đã chấm)
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

from ml.evaluate import bm25_scores, encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load_labels(human: bool):
    if human:
        from openpyxl import load_workbook
        ws = load_workbook(ROOT / "data/annotation/annotate_test.xlsx").active
        out = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and row[7] is not None and str(row[7]).strip() in ("0", "1", "2"):
                jid, cid = row[0].split("_")
                out[(jid, cid)] = int(row[7])
        return out
    out = {}
    for line in open(ROOT / "data/llm/label_reviews.jsonl", encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r["source"] == "annotation":
            out[(r["job_id"], r["cv_id"])] = r["llm_label"]
    return out


def ndcg(scores, labels, k=10):
    order = np.argsort(-scores)[:k]
    dcg = sum((2 ** labels[i] - 1) / math.log2(r + 2) for r, i in enumerate(order))
    ideal = sorted(labels, reverse=True)[:k]
    idcg = sum((2 ** l - 1) / math.log2(r + 2) for r, l in enumerate(ideal))
    return dcg / idcg if idcg else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=["bm25", "skill", "e5-base", "e5-base+hybrid"])
    ap.add_argument("--text", default="profile", choices=["profile", "full"])
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    labels = load_labels(a.human)
    jobs = {j["job_id"]: j for j in map(json.loads, open(ROOT / "data/final/jobs.jsonl", encoding="utf-8"))}
    cvs = {c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final/cvs.jsonl", encoding="utf-8"))}
    groups = collections.defaultdict(list)
    for (j, c), l in labels.items():
        groups[j].append((c, l))
    groups = {j: v for j, v in groups.items() if len({l for _, l in v}) > 1}   # cần ít nhất 2 mức nhãn
    key = f"text_{a.text}"
    print(f"Nhãn {'chấm tay' if a.human else 'LLM'}: {sum(len(v) for v in groups.values())} cặp, {len(groups)} JD, "
          f"phân bố {dict(collections.Counter(l for v in groups.values() for _, l in v))}")

    jids = sorted(groups)
    all_c = sorted({c for v in groups.values() for c, _ in v})
    cidx = {c: i for i, c in enumerate(all_c)}
    q_texts = [jobs[j][key] for j in jids]
    c_texts = [cvs[c][key] for c in all_c]
    skill = np.zeros((len(jids), len(all_c)), dtype=np.float32)
    exp = np.zeros_like(skill)
    for i, j in enumerate(jids):
        js = set(jobs[j]["skills"])
        for c, k in cidx.items():
            skill[i, k] = len(js & set(cvs[c]["skills"])) / len(js)
            my = jobs[j]["min_years"]
            exp[i, k] = 1.0 if my <= 0 else min(1.0, cvs[c]["years"] / my)

    results, cache = {}, {}
    for m in a.methods:
        base, hybrid = m.split("+")[0], m.endswith("+hybrid")
        if base == "bm25":
            sc = bm25_scores(q_texts, c_texts)
        elif base == "skill":
            sc = skill + 0.01 * exp
        else:
            if base not in cache:
                prefix = "query: " if "e5" in base.lower() else ""
                cache[base] = encode(base, q_texts, prefix) @ encode(base, c_texts, prefix).T
            sc = cache[base]
            if hybrid:
                sc = 0.6 * np.clip((sc - 0.5) / 0.5, 0, 1) + 0.3 * skill + 0.1 * exp
        nd, p3, pair_ok, pair_n = [], [], 0, 0
        for i, j in enumerate(jids):
            items = groups[j]
            s = np.array([sc[i, cidx[c]] for c, _ in items])
            lab = [l for _, l in items]
            v = ndcg(s, lab)
            if v is not None:
                nd.append(v)
            top3 = np.argsort(-s)[:3]
            p3.append(np.mean([lab[t] >= 1 for t in top3]))
            for x in range(len(items)):
                for y in range(len(items)):
                    if lab[x] > lab[y]:
                        pair_n += 1
                        pair_ok += s[x] > s[y]
        results[m] = {"ndcg@10": round(float(np.mean(nd)), 4), "p@3": round(float(np.mean(p3)), 4),
                      "pair_acc": round(float(pair_ok / pair_n), 4)}
        print(f"{m:45} {results[m]}", flush=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"labels": "human" if a.human else "llm", "text": a.text, "results": results},
                  open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
