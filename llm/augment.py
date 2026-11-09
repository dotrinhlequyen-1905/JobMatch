"""Tăng cường dữ liệu bằng LLM (OpenRouter free), chạy nền và tự tiếp tục.

  python llm/augment.py            # chạy tới khi xong hết việc (ngủ chờ quota reset nếu hết)
  python llm/augment.py --once     # chạy tới khi hết quota hôm nay thì dừng
  python llm/augment.py --only review --review-batch 16   # chỉ review nhãn, 16 cặp/request
  python llm/augment.py --max-requests 2                   # dừng sau 2 request (để thử)

Tác vụ (xen kẽ, ưu tiên theo thứ tự):
  rewrite : viết lại CV template cho tự nhiên (giữ nguyên dữ kiện) -> data/llm/cv_rewrites.jsonl
  review  : LLM chấm lại nhãn cặp JD-CV                              -> data/llm/label_reviews.jsonl
Kết quả ghi nối tiếp, chạy lại sẽ bỏ qua mục đã xong.
"""
import datetime as dt
import json
import random
import re
import sys
import time
from pathlib import Path

from llm.openrouter import _request, chat                        # noqa: E402
from llm.prompts import REVIEW_SYSTEM_GROUPED, parse_json, review_user_grouped  # noqa: E402
from data_pipeline.vocab import SURFACE_VARIANTS                           # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/llm"
REWRITE_MODELS = ["nvidia/nemotron-3-super-120b-a12b:free", "qwen/qwen3.8-27b:free", "google/gemma-4-31b-it:free"]
REVIEW_MODELS = ["nvidia/nemotron-3-ultra-550b-a55b:free", "dots-studio/dots-3-note-preview:free",
                 "nvidia/nemotron-3-super-120b-a12b:free"]
REWRITE_BATCH, REVIEW_BATCH = 2, 8
# kỹ năng chung chung được phép LLM thêm (tối đa 2); sẽ cập nhật vào danh sách kỹ năng của CV khi gộp
GENERIC_OK = {"Git", "Agile/Scrum", "Jira", "CI/CD", "SQL", "RESTful API", "Confluence", "Postman", "Linux",
              "DevOps", "ETL", "Microservices", "Docker"}
MAX_GENERIC_EXTRA = 2
MAX_REWRITE_TRIES = 2
KEEP_QUOTA = 1
IGNORE_EXTRA = {"C", "Go", "R", "Dart", "Swift", "Spring", "Express.js", "Flow", "Realm", "Unity", "Apache",
                "Ant Design", "Server", "Database", "Monitoring", "Cloud", "Security", "Testing", "Design",
                "Networking", "Excel", "Communication", "Leadership", "Analytics", "Mobile", "Web",
                "Automation", "Backend", "Frontend", "Performance", "Integration", "Scalability"}

REWRITE_SYSTEM = """Bạn là chuyên gia tuyển dụng IT tại Việt Nam. Viết lại các CV dưới đây cho tự nhiên như CV thật
do ứng viên tự viết (câu văn đa dạng, có số liệu, có chi tiết công việc cụ thể, hợp lý với vai trò).
Quy tắc bắt buộc:
- GIỮ NGUYÊN: họ tên, chức danh, email, số điện thoại, thành phố, tên công ty, thời gian làm việc, trường, ngành, GPA, chứng chỉ.
- Mọi kỹ năng trong "skills" phải xuất hiện trong CV (có thể dùng biến thể thông dụng: ReactJS cho React...).
- CHỈ dùng các công nghệ trong "skills" của CHÍNH CV đó. KHÔNG thêm công nghệ/công cụ/ngôn ngữ/framework/nền tảng
  nào khác (kể cả iOS, Android, Jira, Git, SQL... nếu không có trong danh sách). Không mượn kỹ năng giữa các CV.
  Được thêm kỹ năng mềm (giao tiếp, làm việc nhóm...).
- Mỗi kỹ năng đặt vào ngữ cảnh hợp lý (không viết kiểu "vẽ wireframe bằng Java").
- Đúng ngôn ngữ "lang" (vi: tiếng Việt, thuật ngữ công nghệ giữ tiếng Anh; en: tiếng Anh).
- Trình bày dạng văn bản thuần, các mục có tiêu đề, gạch đầu dòng bằng "- ". Độ dài 180-350 từ.
Chỉ trả về JSON: {"cvs": [{"id": "...", "text": "..."}]}"""


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def log(*a):
    print(f"[{dt.datetime.now():%H:%M:%S}]", *a, flush=True)


def load_jsonl(p):
    """Đọc jsonl, bỏ qua dòng hỏng (vd dòng cuối ghi dở khi bị ngắt giữa chừng)."""
    if not Path(p).exists():
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def append(p, row):
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def quota_left():
    try:
        return _request("/key")["data"]["free_model_daily_requests"]["remaining"]
    except Exception as e:
        log("không đọc được quota:", e)
        return 0


def sleep_until_reset():
    t = now_utc()
    nxt = (t + dt.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    log(f"Hết quota. Ngủ tới {nxt.astimezone():%Y-%m-%d %H:%M} (giờ máy)")
    time.sleep((nxt - t).total_seconds())


# ---------------------------------------------------------------------------
def skill_in(text, skill):
    t = text.lower()
    return any(re.search(r"(?<![\w.#+])" + re.escape(v.lower()) + r"(?![\w#+])", t)
               for v in SURFACE_VARIANTS.get(skill, []) + [skill])


def rewrite_spec(cv):
    return {"id": cv["cv_id"], "lang": cv["lang"], "name": cv["name"], "title": cv["title"],
            "email": cv["email"], "phone": cv["phone"], "city": cv["city"], "years_experience": cv["years"],
            "skills": cv["skills"],
            "experience": [{"company": j["company"], "position": j["position"], "start": j["start"],
                            "end": j["end"] or "now"} for j in cv["experience"]],
            "education": cv["education"], "certifications": cv["certs"],
            "template_draft": cv["text"]}


def check_rewrite(cv, text, vocab):
    if not text or len(text.split()) < 120:
        return ["quá ngắn"]
    errs = []
    missing = [s for s in cv["skills"] if not skill_in(text, s)]
    if missing:
        errs.append(f"thiếu kỹ năng {missing}")
    extra = [s for s in vocab if s not in cv["skills"] and s not in IGNORE_EXTRA and skill_in(text, s)]
    bad = [s for s in extra if s not in GENERIC_OK]
    if bad or len(extra) > MAX_GENERIC_EXTRA:
        errs.append(f"thêm kỹ năng {extra}")
    if cv["name"].split()[-1].lower() not in text.lower():
        errs.append("sai tên")
    vi = len(re.findall(r"[ạảấầẩẫậắằẳẵặẹẻẽếềểễệịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ]", text.lower())) / len(text) > 0.015
    if vi != (cv["lang"] == "vi"):
        errs.append("sai ngôn ngữ")
    return errs


def call_models(models, system, user, max_tokens, temperature, bad_models):
    for m in models:
        if m in bad_models:
            continue
        text, info = chat(m, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                          temperature=temperature, max_tokens=max_tokens, retries=2)
        parsed = parse_json(text)
        if parsed is not None:
            return m, parsed, info
        err = info.get("error", "") or "JSON lỗi/bị cắt"
        log(f"  {m} lỗi: {err[:120]}")
        if "403" in err or "404" in err:
            bad_models.add(m)
    return None, None, None


# ---------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--only", choices=["review", "rewrite", "both"], default="both")
    ap.add_argument("--review-batch", type=int, default=REVIEW_BATCH)
    ap.add_argument("--max-requests", type=int, default=0)
    ap.add_argument("--rewrite-splits", nargs="+", default=["test", "val", "train"],
                    help="tập CV cần viết lại, theo thứ tự ưu tiên (vd: --rewrite-splits test)")
    args = ap.parse_args()
    once = args.once
    n_requests = 0
    OUT.mkdir(parents=True, exist_ok=True)
    rw_path, rv_path = OUT / "cv_rewrites.jsonl", OUT / "label_reviews.jsonl"
    jobs = {j["job_id"]: j for j in load_jsonl(ROOT / "data/final/jobs.jsonl")}
    cvs = {c["cv_id"]: c for c in load_jsonl(ROOT / "data/final/cvs.jsonl")}
    vocab = [s for s, n in json.load(open(ROOT / "data/processed/skills_vocab.json", encoding="utf-8"))["freq"].items()
             if n >= 5]

    # hàng đợi rewrite: test -> val -> train (ngẫu nhiên trong mỗi tập)
    rng = random.Random(0)
    rw_queue = []
    for sp in args.rewrite_splits:
        ids = [c for c, v in cvs.items() if v["split"] == sp]
        rng.shuffle(ids)
        rw_queue += ids
    # hàng đợi review: tập gán nhãn tay -> cặp train sinh ra
    key = json.load(open(ROOT / "data/annotation/annotation_key.json", encoding="utf-8"))
    rv_queue = [("annotation", *t.split("_"), lbl) for t, lbl in key.items()]
    pairs = load_jsonl(ROOT / "data/processed/pairs.jsonl")
    train_pairs = [("train_pair", p["job_id"], p["cv_id"], p["label"]) for p in pairs
                   if jobs[p["job_id"]]["split"] == "train"]
    # xáo theo JD nhưng giữ các cặp cùng JD cạnh nhau -> gộp được JD trong 1 request
    by_job = {}
    for t in train_pairs:
        by_job.setdefault(t[1], []).append(t)
    job_order = sorted(by_job)
    rng.shuffle(job_order)
    rv_queue += [t for j in job_order for t in by_job[j]]
    if args.only == "review":
        rw_queue = []
    elif args.only == "rewrite":
        rv_queue = []

    bad_models = set()
    turn = fails = 0
    while True:
        # CV coi là xong khi đã có bản đạt, hoặc đã thử MAX_REWRITE_TRIES lần mà vẫn lỗi
        rw_rows = load_jsonl(rw_path)
        tries = {}
        for r in rw_rows:
            tries[r["cv_id"]] = tries.get(r["cv_id"], 0) + 1
        done_rw = {r["cv_id"] for r in rw_rows if r["ok"]} | {c for c, n in tries.items() if n >= MAX_REWRITE_TRIES}
        done_rv = {(r["job_id"], r["cv_id"]) for r in load_jsonl(rv_path)}
        todo_rw = [c for c in rw_queue if c not in done_rw]
        todo_rv = [q for q in rv_queue if (q[1], q[2]) not in done_rv]
        if not todo_rw and not todo_rv:
            log("Xong toàn bộ.")
            return
        left = quota_left()
        log(f"quota còn {left} | rewrite còn {len(todo_rw)} | review còn {len(todo_rv)}")
        if args.max_requests and n_requests >= args.max_requests:
            return
        n_requests += 1
        if left <= KEEP_QUOTA:
            if once:
                return
            sleep_until_reset()
            continue

        task = "rewrite" if (turn % 2 == 0 and todo_rw) or not todo_rv else "review"
        turn += 1
        if task == "rewrite":
            batch = [cvs[c] for c in todo_rw[:REWRITE_BATCH]]
            user = json.dumps({"cvs": [rewrite_spec(c) for c in batch]}, ensure_ascii=False)
            m, parsed, info = call_models(REWRITE_MODELS, REWRITE_SYSTEM, user, 12000, 0.7, bad_models)
            if not parsed:
                fails += 1
                time.sleep(1800 if fails >= 4 else 60)
                continue
            fails = 0
            got = {x.get("id"): x.get("text", "") for x in parsed.get("cvs", []) if isinstance(x, dict)}
            for cv in batch:
                text = got.get(cv["cv_id"], "")
                errs = check_rewrite(cv, text, vocab)
                added = [s for s in vocab if s in GENERIC_OK and s not in cv["skills"] and skill_in(text, s)]
                append(rw_path, {"cv_id": cv["cv_id"], "split": cv["split"], "model": m, "ok": not errs,
                                 "errors": errs, "added_skills": added if not errs else [], "text": text,
                                 "ts": now_utc().isoformat()})
            log(f"rewrite {len(batch)} CV bằng {m} ({info.get('sec')}s): "
                f"{sum(not check_rewrite(c, got.get(c['cv_id'], ''), vocab) for c in batch)} đạt")
        else:
            items = todo_rv[:args.review_batch]
            cases = [{"id": f"p{i}", "job": jobs[j], "cv": cvs[c]} for i, (_, j, c, _) in enumerate(items)]
            m, parsed, info = call_models(REVIEW_MODELS, REVIEW_SYSTEM_GROUPED, review_user_grouped(cases),
                                          16000 + 700 * len(items), 0.0, bad_models)
            if not parsed:
                fails += 1
                time.sleep(1800 if fails >= 4 else 60)
                continue
            fails = 0
            res = {r.get("id"): r for r in parsed.get("results", []) if isinstance(r, dict)}
            n_ok = 0
            for i, (src, j, c, lbl) in enumerate(items):
                r = res.get(f"p{i}")
                if not r or r.get("label") not in (0, 1, 2):
                    continue
                n_ok += 1
                append(rv_path, {"source": src, "job_id": j, "cv_id": c, "rule_label": lbl, "llm_label": r["label"],
                                 "matched_skills": r.get("matched_skills", []),
                                 "missing_skills": r.get("missing_skills", []), "reason": r.get("reason", ""),
                                 "model": m, "ts": now_utc().isoformat()})
            log(f"review {n_ok}/{len(items)} cặp bằng {m} ({info.get('sec')}s)")


if __name__ == "__main__":
    main()
