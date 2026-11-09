"""Bước 5: tạo file Excel để gán nhãn tay -> data/annotation/annotate_test.xlsx

50 JD của tập test, mỗi JD 10 CV (xáo trộn, không hiện nhãn máy):
  2 CV rel=2, 3 CV rel=1, 2 CV "gây nhầm" (cùng/gần vai trò nhưng rel=0), 3 CV ngẫu nhiên.
Nhãn máy lưu riêng ở annotation_key.json để so sánh sau khi chấm tay.
"""
import collections
import json
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from data_pipeline.s03_split_export import relevance
from data_pipeline.vocab import RELATED_ROLES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/annotation"
N_JOBS, SEED = 50, 11
QUOTA = {"rel2": 2, "rel1": 3, "tricky": 2, "random": 3}

GUIDE = [
    ("2 - Phù hợp", "Đúng vai trò, có hầu hết kỹ năng bắt buộc, đủ (hoặc gần đủ) số năm kinh nghiệm. Bạn sẽ mời phỏng vấn."),
    ("1 - Phù hợp một phần", "Cùng/gần vai trò nhưng thiếu một số kỹ năng quan trọng hoặc thiếu kinh nghiệm. Có thể cân nhắc."),
    ("0 - Không phù hợp", "Khác vai trò, hoặc thiếu phần lớn kỹ năng cốt lõi. Không mời phỏng vấn."),
    ("Lưu ý", "Chấm theo cảm nhận của nhà tuyển dụng, KHÔNG đếm máy móc số kỹ năng trùng. "
              "Ghi chú lý do ở cột note nếu phân vân."),
]


def main():
    rng = random.Random(SEED)
    jobs = [json.loads(l) for l in open(ROOT / "data/final/jobs.jsonl", encoding="utf-8")]
    cvs = [json.loads(l) for l in open(ROOT / "data/final/cvs.jsonl", encoding="utf-8")]
    test_jobs = [j for j in jobs if j["split"] == "test"]
    test_cvs = [c for c in cvs if c["split"] == "test"]

    # lấy JD theo vai trò cho đa dạng (round-robin qua các nhóm)
    by_role = collections.defaultdict(list)
    for j in test_jobs:
        by_role[j["role"]].append(j)
    for v in by_role.values():
        rng.shuffle(v)
    chosen = []
    while len(chosen) < N_JOBS and any(by_role.values()):
        for r in sorted(by_role):
            if by_role[r] and len(chosen) < N_JOBS:
                chosen.append(by_role[r].pop())

    rows, key = [], {}
    for job in chosen:
        rel = {c["cv_id"]: relevance(job, c) for c in test_cvs}
        near = {job["role"]} | RELATED_ROLES.get(job["role"], set())
        pools = {
            "rel2": [c for c in test_cvs if rel[c["cv_id"]] == 2],
            "rel1": [c for c in test_cvs if rel[c["cv_id"]] == 1],
            "tricky": [c for c in test_cvs if rel[c["cv_id"]] == 0 and c["role"] in near],
            "random": [c for c in test_cvs if rel[c["cv_id"]] == 0],
        }
        picked = []
        for name, n in QUOTA.items():
            cand = [c for c in pools[name] if c not in picked]
            picked += rng.sample(cand, min(n, len(cand)))
        while len(picked) < sum(QUOTA.values()):  # bù nếu nhóm nào thiếu
            c = rng.choice(test_cvs)
            if c not in picked:
                picked.append(c)
        rng.shuffle(picked)
        for c in picked:
            tid = f"{job['job_id']}_{c['cv_id']}"
            key[tid] = rel[c["cv_id"]]
            rows.append((tid, job, c))

    OUT.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "annotate"
    header = ["task_id", "jd_title", "jd_level", "jd_skills", "jd_description", "cv_id", "cv_text",
              "human_label (0/1/2)", "note"]
    ws.append(header)
    for tid, job, c in rows:
        ws.append([tid, job["title"], f"{job['seniority']}, >= {job['min_years']} năm",
                   ", ".join(job["skills"]), job["description"][:1500], c["cv_id"], c["text"], None, None])
    widths = [20, 28, 16, 30, 60, 9, 70, 12, 25]
    for col, w in zip("ABCDEFGHI", widths):
        ws.column_dimensions[col].width = w
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        row[7].fill = PatternFill("solid", fgColor="FFF2CC")
    dv = DataValidation(type="list", formula1='"0,1,2"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{len(rows) + 1}")
    ws.freeze_panes = "C2"

    g = wb.create_sheet("huong_dan")
    g.append(["Nhãn", "Ý nghĩa"])
    for r in GUIDE:
        g.append(list(r))
    g.column_dimensions["A"].width, g.column_dimensions["B"].width = 22, 110
    for cell in g[1]:
        cell.font = Font(bold=True)

    wb.save(OUT / "annotate_test.xlsx")
    with open(OUT / "annotation_key.json", "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=0)
    dist = collections.Counter(key.values())
    print(f"Đã tạo {len(rows)} dòng cần chấm ({len(chosen)} JD). Nhãn máy: {dict(sorted(dist.items()))}")
    print("Vai trò:", dict(collections.Counter(j["role"] for j in chosen)))


if __name__ == "__main__":
    main()
