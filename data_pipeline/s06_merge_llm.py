"""Bước 6: gộp kết quả LLM (llm/augment.py) vào bộ dữ liệu. Chạy lại bất cứ lúc nào khi có thêm kết quả.

Đầu ra:
  data/final/cvs_llm.jsonl            CV đã được LLM viết lại (text_full/text_profile mới, kỹ năng cập nhật)
  data/final/{val,test}_llm_ir.json    tập đánh giá dùng CV viết lại (giống CV thật hơn), qrels chấm lại
  data/final/train_triplets_{full,profile}_llm.jsonl   thêm bộ ba dùng CV viết lại (tăng đa dạng câu chữ)
  data/final/train_triplets_{full,profile}_clean.jsonl bộ ba gốc, bỏ những bộ LLM cho là nhãn sai
  data/llm/review_report.txt, review_disagreements.csv   so sánh nhãn luật vs nhãn LLM
"""
import collections
import csv
import json
from pathlib import Path

from data_pipeline.profile_text import cv_profile, jd_full, jd_profile
from data_pipeline.s03_split_export import relevance

ROOT = Path(__file__).resolve().parents[1]
FINAL, LLM = ROOT / "data/final", ROOT / "data/llm"


def jl(p):
    if not Path(p).exists():
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:   # dòng ghi dở khi augment bị ngắt
            pass
    return out


def dump(p, rows):
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    jobs = {j["job_id"]: j for j in jl(FINAL / "jobs.jsonl")}
    cvs = {c["cv_id"]: c for c in jl(FINAL / "cvs.jsonl")}
    rewrites = {r["cv_id"]: r for r in jl(LLM / "cv_rewrites.jsonl") if r["ok"]}
    reviews = jl(LLM / "label_reviews.jsonl")

    # ---------------- CV viết lại
    llm_cvs = {}
    for cid, r in rewrites.items():
        c = dict(cvs[cid])
        c["skills"] = c["skills"] + [s for s in r.get("added_skills", []) if s not in c["skills"]]
        c["text"] = c["text_full"] = r["text"]
        c["text_profile"] = cv_profile(c)
        c["llm_model"] = r["model"]
        llm_cvs[cid] = c
    dump(FINAL / "cvs_llm.jsonl", llm_cvs.values())
    print(f"CV viết lại hợp lệ: {len(llm_cvs)} (test {sum(c['split'] == 'test' for c in llm_cvs.values())}, "
          f"val {sum(c['split'] == 'val' for c in llm_cvs.values())}, "
          f"train {sum(c['split'] == 'train' for c in llm_cvs.values())})")

    for sp in ("val", "test"):
        js = [j for j in jobs.values() if j["split"] == sp]
        cs = [c for c in llm_cvs.values() if c["split"] == sp]
        if not cs:
            continue
        qrels = {j["job_id"]: {c["cv_id"]: r for c in cs if (r := relevance(j, c)) > 0} for j in js}
        qrels = {q: v for q, v in qrels.items() if v}
        json.dump({"queries": list(qrels), "corpus": [c["cv_id"] for c in cs], "qrels": qrels,
                   "cv_source": "cvs_llm.jsonl"}, open(FINAL / f"{sp}_llm_ir.json", "w", encoding="utf-8"))
        print(f"  {sp}_llm_ir: {len(qrels)} JD có CV liên quan / {len(cs)} CV")

    # ---------------- review nhãn
    by_pair = {(r["job_id"], r["cv_id"]): r for r in reviews}
    conf = collections.defaultdict(collections.Counter)
    rows = []
    for r in reviews:
        conf[r["source"]][(r["rule_label"], r["llm_label"])] += 1
        if r["rule_label"] != r["llm_label"]:
            j, c = jobs[r["job_id"]], cvs[r["cv_id"]]
            rows.append({"source": r["source"], "job_id": r["job_id"], "cv_id": r["cv_id"], "jd_title": j["title"],
                         "jd_skills": ", ".join(j["skills"]), "cv_title": c["title"], "cv_skills": ", ".join(c["skills"]),
                         "rule": r["rule_label"], "llm": r["llm_label"], "reason": r["reason"]})
    lines = [f"Tổng số cặp LLM đã review: {len(reviews)}"]
    for src, cnt in conf.items():
        n = sum(cnt.values())
        agree = sum(v for (a, b), v in cnt.items() if a == b)
        lines.append(f"\n[{src}] {n} cặp, đồng ý {agree / n:.1%}")
        lines.append("  luật\\LLM    0     1     2")
        for a in (0, 1, 2):
            lines.append(f"  {a:9} " + " ".join(f"{cnt[(a, b)]:5}" for b in (0, 1, 2)))
    report = "\n".join(lines)
    (LLM / "review_report.txt").write_text(report, encoding="utf-8")
    with open(LLM / "review_disagreements.csv", "w", encoding="utf-8-sig", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(report)

    # ---------------- bộ ba train: bản sạch + bản dùng CV viết lại
    for mode in ("full", "profile"):
        base = jl(FINAL / f"train_triplets_{mode}.jsonl")
        pairs = {p["job_id"]: {} for p in []}
        for p in jl(ROOT / "data/processed/pairs.jsonl"):
            pairs.setdefault(p["job_id"], {})[p["kind"]] = p["cv_id"]
        clean, dropped, extra = [], 0, []
        for t in base:
            kinds = pairs[t["job_id"]]
            pos, neg = kinds["fit"], kinds[t["neg_kind"]]
            rp, rn = by_pair.get((t["job_id"], pos)), by_pair.get((t["job_id"], neg))
            if (rp and rp["llm_label"] < 2) or (rn and rn["llm_label"] == 2):
                dropped += 1
                continue
            clean.append(t)
            if pos in llm_cvs or neg in llm_cvs:
                j = jobs[t["job_id"]]
                txt = (lambda c: c["text_full"]) if mode == "full" else (lambda c: c["text_profile"])
                extra.append({**t, "anchor": jd_full(j) if mode == "full" else jd_profile(j),
                              "positive": txt(llm_cvs.get(pos, cvs[pos])), "negative": txt(llm_cvs.get(neg, cvs[neg])),
                              "llm": True})
        dump(FINAL / f"train_triplets_{mode}_clean.jsonl", clean)
        dump(FINAL / f"train_triplets_{mode}_llm.jsonl", clean + extra)
        print(f"[{mode}] triplets gốc {len(base)} -> sạch {len(clean)} (bỏ {dropped}) | +{len(extra)} bộ dùng CV viết lại")


if __name__ == "__main__":
    main()
