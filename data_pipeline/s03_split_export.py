"""Bước 3: chia train/val/test theo JD và xuất dữ liệu train/đánh giá -> data/final/

Xuất ra:
  jobs.jsonl, cvs.jsonl                 JD/CV kèm split, text full và profile
  train_triplets_{full,profile}.jsonl   (anchor=JD, positive=CV phù hợp, negative=CV không/ít phù hợp)
  train_pairs_{full,profile}.jsonl      (jd, cv, score 0/0.5/1) cho cross-encoder / CoSENT
  {val,test}_ir.json                    queries (JD), corpus (CV), qrels chấm trên toàn ma trận JD x CV
"""
import collections
import json
import random
from pathlib import Path

from data_pipeline.profile_text import cv_full, cv_profile, jd_full, jd_profile
from data_pipeline.vocab import RELATED_ROLES

ROOT = Path(__file__).resolve().parents[1]
PROC, FINAL = ROOT / "data/processed", ROOT / "data/final"
SEED = 42
RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}


def load(name):
    return [json.loads(l) for l in open(PROC / name, encoding="utf-8")]


def dump_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def split_jobs(jobs):
    """Chia theo JD, phân tầng theo vai trò để tập nào cũng có đủ các nhóm."""
    rng = random.Random(SEED)
    by_role = collections.defaultdict(list)
    for j in jobs:
        by_role[j["role"]].append(j["job_id"])
    split = {}
    for ids in by_role.values():
        rng.shuffle(ids)
        n_val = max(1, round(len(ids) * RATIOS["val"]))
        n_test = max(1, round(len(ids) * RATIOS["test"]))
        for i, jid in enumerate(ids):
            split[jid] = "val" if i < n_val else "test" if i < n_val + n_test else "train"
    return split


def relevance(job, cv):
    """Luật chấm mức phù hợp (0/1/2), dùng chung cho mọi cặp JD x CV trong val/test."""
    jd = set(job["skills"])
    cov = len(jd & set(cv["skills"])) / len(jd)
    same = cv["role"] == job["role"]
    related = cv["role"] in RELATED_ROLES.get(job["role"], set())
    if same and cov >= 0.7 and cv["years"] >= job["min_years"] - 1:
        return 2
    if (same and cov >= 0.4) or (related and cov >= 0.6):
        return 1
    return 0


def main():
    jobs, cvs, pairs = load("jobs.jsonl"), load("cvs.jsonl"), load("pairs.jsonl")
    job_by_id = {j["job_id"]: j for j in jobs}
    cv_by_id = {c["cv_id"]: c for c in cvs}
    split = split_jobs(jobs)
    cv_split = {p["cv_id"]: split[p["job_id"]] for p in pairs}

    FINAL.mkdir(parents=True, exist_ok=True)
    dump_jsonl(FINAL / "jobs.jsonl", [
        {**j, "split": split[j["job_id"]], "text_full": jd_full(j), "text_profile": jd_profile(j)} for j in jobs])
    dump_jsonl(FINAL / "cvs.jsonl", [
        {**c, "split": cv_split[c["cv_id"]], "text_full": cv_full(c), "text_profile": cv_profile(c)} for c in cvs])

    # --- train ---------------------------------------------------------------
    by_job = collections.defaultdict(dict)
    for p in pairs:
        by_job[p["job_id"]][p["kind"]] = p["cv_id"]
    for mode, jf, cf in (("full", jd_full, cv_full), ("profile", jd_profile, cv_profile)):
        triplets, scored = [], []
        for jid, kinds in by_job.items():
            if split[jid] != "train":
                continue
            job = job_by_id[jid]
            fit = cv_by_id[kinds["fit"]]
            for neg_kind in ("hard_neg", "partial_skill", "partial_senior"):
                if neg_kind in kinds:
                    triplets.append({"anchor": jf(job), "positive": cf(fit),
                                     "negative": cf(cv_by_id[kinds[neg_kind]]),
                                     "job_id": jid, "neg_kind": neg_kind})
        for p in pairs:
            if split[p["job_id"]] == "train":
                scored.append({"jd": jf(job_by_id[p["job_id"]]), "cv": cf(cv_by_id[p["cv_id"]]),
                               "score": p["label"] / 2, "job_id": p["job_id"], "cv_id": p["cv_id"]})
        dump_jsonl(FINAL / f"train_triplets_{mode}.jsonl", triplets)
        dump_jsonl(FINAL / f"train_pairs_{mode}.jsonl", scored)
        print(f"[{mode}] triplets: {len(triplets)}, pairs có điểm: {len(scored)}")

    # --- val / test: chấm toàn bộ ma trận JD x CV ---------------------------------
    for name in ("val", "test"):
        js = [j for j in jobs if split[j["job_id"]] == name]
        cs = [c for c in cvs if cv_split[c["cv_id"]] == name]
        qrels = {}
        dist = collections.Counter()
        for j in js:
            rels = {c["cv_id"]: r for c in cs if (r := relevance(j, c)) > 0}
            qrels[j["job_id"]] = rels
            dist.update(rels.values())
        # kiểm tra luật chấm khớp với nhãn gốc lúc sinh
        agree = [relevance(job_by_id[p["job_id"]], cv_by_id[p["cv_id"]]) == p["label"]
                 for p in pairs if split[p["job_id"]] == name]
        with open(FINAL / f"{name}_ir.json", "w", encoding="utf-8") as f:
            json.dump({"queries": [j["job_id"] for j in js], "corpus": [c["cv_id"] for c in cs],
                       "qrels": qrels}, f, ensure_ascii=False)
        print(f"[{name}] {len(js)} JD x {len(cs)} CV | cặp rel=2: {dist[2]}, rel=1: {dist[1]} "
              f"| TB {sum(len(v) for v in qrels.values()) / len(js):.1f} CV liên quan/JD "
              f"| luật khớp nhãn gốc: {sum(agree) / len(agree):.1%}")

    print("\nPhân bố vai trò theo split:")
    tab = collections.Counter((j["role"], split[j["job_id"]]) for j in jobs)
    for r in sorted({j["role"] for j in jobs}):
        print(f"  {r:18} train={tab[(r, 'train')]:4} val={tab[(r, 'val')]:3} test={tab[(r, 'test')]:3}")


if __name__ == "__main__":
    main()
