"""So sánh các model free trên OpenRouter cho 2 tác vụ: sinh CV và review nhãn.

Mỗi model dùng 2 request (quota free: 50 request/ngày). Kết quả -> llm/results/
"""
import json
import re
import sys
from pathlib import Path

from llm.openrouter import chat                                   # noqa: E402
from llm.prompts import GEN_SYSTEM, REVIEW_SYSTEM, gen_user, parse_json, review_user  # noqa: E402
from data_pipeline.vocab import ROLE_DISPLAY, SURFACE_VARIANTS              # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "llm/results"
MODELS = [
    "qwen/qwen3.8-27b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "thinkingmachines/inkling:free",
    "thinkingmachines/inkling-small:free",
    "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3.5-lightning:free",
]
# kỹ năng tên quá ngắn/dễ trùng từ thường -> không dùng để phát hiện "kỹ năng bịa"
AMBIGUOUS = {"C", "Go", "R", "Dart", "Swift", "Spring", "Express.js", "Flow", "Realm", "Unity", "Apache", "Ant Design"}


def load():
    jobs = {j["job_id"]: j for j in map(json.loads, open(ROOT / "data/final/jobs.jsonl", encoding="utf-8"))}
    cvs = {c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final/cvs.jsonl", encoding="utf-8"))}
    vocab = json.load(open(ROOT / "data/processed/skills_vocab.json", encoding="utf-8"))["skills"]
    return jobs, cvs, vocab


def pick_cases(jobs, cvs):
    """6 cặp review lấy từ tập gán nhãn: 2 rel2, 2 rel1, 1 rel0 cùng vai trò (gây nhầm), 1 rel0 khác vai trò."""
    key = json.load(open(ROOT / "data/annotation/annotation_key.json", encoding="utf-8"))
    want = {"2": 2, "1": 2, "0same": 1, "0diff": 1}
    cases = []
    for tid, rel in key.items():
        jid, cid = tid.split("_")
        job, cv = jobs[jid], cvs[cid]
        b = str(rel) if rel else ("0same" if cv["role"] == job["role"] else "0diff")
        if want.get(b, 0) > 0 and all(c["job"]["job_id"] != jid for c in cases):
            want[b] -= 1
            cases.append({"id": f"case{len(cases) + 1}", "job": job, "cv": cv, "rule_label": rel, "bucket": b})
    return cases


def gen_specs(jobs, cvs):
    """Spec sinh CV dựa trên 1 JD của tập test: 1 CV fit (vi) + 1 CV partial_senior (en)."""
    pairs = [json.loads(l) for l in open(ROOT / "data/processed/pairs.jsonl", encoding="utf-8")]
    job = next(j for j in jobs.values() if j["split"] == "test" and j["role"] == "backend" and j["min_years"] >= 3
               and 6 <= len(j["skills"]) <= 9)
    fit = cvs[next(p["cv_id"] for p in pairs if p["job_id"] == job["job_id"] and p["kind"] == "fit")]
    specs = [
        {"id": "fit_vi", "role_display": ROLE_DISPLAY[job["role"]][0], "seniority": fit["seniority"],
         "years": fit["years"], "lang": "vi", "skills": fit["skills"], "note": "Ứng viên rất phù hợp với JD."},
        {"id": "senior_gap_en", "role_display": ROLE_DISPLAY[job["role"]][1], "seniority": "junior",
         "years": max(0, job["min_years"] - 2), "lang": "en", "skills": job["skills"][:-1],
         "note": "Đủ kỹ năng nhưng thiếu kinh nghiệm so với JD."},
    ]
    return job, specs


def skill_in(text, skill):
    t = text.lower()
    return any(re.search(r"(?<![\w.#+])" + re.escape(v.lower()) + r"(?![\w#+])", t)
               for v in SURFACE_VARIANTS.get(skill, [skill]) + [skill])


def check_gen(parsed, specs, vocab):
    out = []
    items = {c.get("id"): c.get("text", "") for c in (parsed or {}).get("cvs", []) if isinstance(c, dict)}
    for s in specs:
        text = items.get(s["id"]) or ""
        if not text:
            out.append({"id": s["id"], "ok": False})
            continue
        missing = [k for k in s["skills"] if not skill_in(text, k)]
        extra = [k for k in vocab if k not in s["skills"] and k not in AMBIGUOUS and skill_in(text, k)]
        vi_ratio = len(re.findall(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text.lower())) / max(len(text), 1)
        out.append({"id": s["id"], "ok": True, "words": len(text.split()), "missing": missing, "extra": extra,
                    "lang_ok": (vi_ratio > 0.02) == (s["lang"] == "vi")})
    return out


def check_review(parsed, cases):
    res = {r.get("id"): r for r in (parsed or {}).get("results", []) if isinstance(r, dict)}
    rows = []
    for c in cases:
        r = res.get(c["id"], {})
        rows.append({"id": c["id"], "bucket": c["bucket"], "rule": c["rule_label"], "llm": r.get("label"),
                     "reason": r.get("reason", "")})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs, cvs, vocab = load()
    job, specs = gen_specs(jobs, cvs)
    cases = pick_cases(jobs, cvs)
    models = sys.argv[1:] or MODELS
    summary = json.load(open(OUT / "summary.json", encoding="utf-8")) if (OUT / "summary.json").exists() else {}

    for m in models:
        print(f"\n######## {m}", flush=True)
        g_text, g_info = chat(m, [{"role": "system", "content": GEN_SYSTEM},
                                  {"role": "user", "content": gen_user(job, specs)}], temperature=0.7, max_tokens=6000)
        r_text, r_info = chat(m, [{"role": "system", "content": REVIEW_SYSTEM},
                                  {"role": "user", "content": review_user(cases)}], temperature=0.0, max_tokens=6000)
        g_parsed, r_parsed = parse_json(g_text), parse_json(r_text)
        gen, rev = check_gen(g_parsed, specs, vocab), check_review(r_parsed, cases)
        slug = m.replace("/", "__").replace(":", "_")
        json.dump({"model": m, "gen_raw": g_text, "gen_info": g_info, "review_raw": r_text, "review_info": r_info,
                   "gen_check": gen, "review_check": rev}, open(OUT / f"{slug}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        summary[m] = {"gen_info": g_info, "review_info": r_info, "gen_json_ok": g_parsed is not None,
                      "review_json_ok": r_parsed is not None, "gen": gen, "review": rev}
        print("gen:", g_info, "| json ok:", g_parsed is not None)
        for x in gen:
            print("  ", x)
        print("review:", r_info, "| json ok:", r_parsed is not None)
        print("   rule vs llm:", [(x["bucket"], x["llm"]) for x in rev])
        json.dump(summary, open(OUT / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump({"job_id": job["job_id"], "specs": specs, "cases": [
        {"id": c["id"], "job_id": c["job"]["job_id"], "cv_id": c["cv"]["cv_id"], "rule_label": c["rule_label"],
         "bucket": c["bucket"]} for c in cases]}, open(OUT / "test_inputs.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
