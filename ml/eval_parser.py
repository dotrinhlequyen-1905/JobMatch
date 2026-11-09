"""Đánh giá module trích xuất CV trên 200 file PDF/DOCX có đáp án (data/cv_files/ground_truth.jsonl).

  python ml/eval_parser.py

Chỉ số: precision/recall/F1 kỹ năng (micro), độ chính xác số năm KN (đúng tuyệt đối / lệch <= 1),
email, số điện thoại, vai trò. Chia theo bố cục file (1 cột, 2 cột, docx).
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from app.ai.cv_parser import parse_cv_file  # noqa: E402


def main():
    truth = [json.loads(l) for l in open(ROOT / "data/cv_files/ground_truth.jsonl", encoding="utf-8")]
    agg = collections.defaultdict(lambda: collections.Counter())
    errors = []
    for t in truth:
        data = (ROOT / "data/cv_files" / t["file"]).read_bytes()
        p = parse_cv_file(data, t["file"])
        for key in (t["layout"], "ALL"):
            a = agg[key]
            gold, pred = set(t["skills"]), set(p["skills"])
            a["tp"] += len(gold & pred)
            a["fp"] += len(pred - gold)
            a["fn"] += len(gold - pred)
            a["n"] += 1
            a["years_exact"] += p["years"] == t["years"]
            a["years_pm1"] += abs(p["years"] - t["years"]) <= 1
            a["email"] += (p["email"] or "").lower() == t["email"].lower()
            a["phone"] += (p["phone"] or "") == t["phone"]
            a["role"] += p["role"] == t["role"]
        if set(t["skills"]) != set(p["skills"]) and len(errors) < 8:
            errors.append((t["file"], sorted(set(t["skills"]) - set(p["skills"])), sorted(set(p["skills"]) - set(t["skills"]))))

    print(f"{'Bố cục':12} {'N':>4} {'P':>6} {'R':>6} {'F1':>6} {'Năm=':>6} {'Năm±1':>6} {'Email':>6} {'SĐT':>6} {'Vai trò':>7}")
    for key in ("pdf_single", "pdf_two_col", "docx", "ALL"):
        a = agg[key]
        p = a["tp"] / max(1, a["tp"] + a["fp"])
        r = a["tp"] / max(1, a["tp"] + a["fn"])
        f1 = 2 * p * r / max(1e-9, p + r)
        n = a["n"]
        print(f"{key:12} {n:4} {p:6.3f} {r:6.3f} {f1:6.3f} {a['years_exact'] / n:6.2%} {a['years_pm1'] / n:6.2%} "
              f"{a['email'] / n:6.2%} {a['phone'] / n:6.2%} {a['role'] / n:7.2%}")
    print("\nVí dụ lệch kỹ năng (file, thiếu, thừa):")
    for e in errors:
        print(" ", e)


if __name__ == "__main__":
    main()
