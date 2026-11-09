"""Bước 1: làm sạch JD thô -> data/processed/jobs.jsonl

- Bỏ tin trùng, tin quá ngắn, tin không thuộc IT.
- Chuẩn hóa kỹ năng, vai trò, cấp bậc, số năm kinh nghiệm, ngôn ngữ.
- Chỉ giữ kỹ năng xuất hiện >= MIN_SKILL_FREQ lần để từ điển không bị nhiễu.
"""
import ast
import collections
import json
import re
from pathlib import Path

import pandas as pd

from data_pipeline.vocab import (min_years_from_text, normalize_role, normalize_skill,
                   seniority_from_title, SENIORITY_YEARS, years_to_seniority)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/IT-Job-Posting/job_descriptions.csv"
OUT_DIR = ROOT / "data/processed"
MIN_DESC_LEN = 300
MIN_SKILL_FREQ = 3
MIN_SKILLS_PER_JOB = 3

VI_CHARS = re.compile(r"[ăâđêôơưàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ]", re.I)


def detect_lang(text: str) -> str:
    return "vi" if len(VI_CHARS.findall(text)) / max(len(text), 1) > 0.03 else "en"


def clean_desc(text: str) -> str:
    text = re.sub(r"\r", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_list(v) -> list:
    try:
        return list(ast.literal_eval(v))
    except (ValueError, SyntaxError):
        return []


def main():
    df = pd.read_csv(RAW)
    n0 = len(df)
    df["description"] = df["description"].astype(str).map(clean_desc)
    df = df[df["description"].str.len() >= MIN_DESC_LEN]
    df = df.drop_duplicates("description").drop_duplicates(["title", "company"])
    print(f"Sau lọc trùng/ngắn: {n0} -> {len(df)}")

    # chuẩn hóa kỹ năng (giữ thứ tự, bỏ trùng)
    def skills_of(row):
        out = []
        for s in parse_list(row["main_programming_languages"]) + parse_list(row["key_technologies"]):
            n = normalize_skill(str(s))
            if n and n not in out:
                out.append(n)
        return out

    df["skills_raw"] = df.apply(skills_of, axis=1)
    freq = collections.Counter(s for lst in df["skills_raw"] for s in lst)
    vocab = {s for s, c in freq.items() if c >= MIN_SKILL_FREQ}
    df["skills"] = df["skills_raw"].map(lambda lst: [s for s in lst if s in vocab])
    df = df[df["skills"].map(len) >= MIN_SKILLS_PER_JOB]
    print(f"Sau lọc JD có >= {MIN_SKILLS_PER_JOB} kỹ năng hợp lệ: {len(df)}")

    df["role"] = [normalize_role(r, t) for r, t in zip(df["it_role_type"], df["title"])]
    df = df[df["role"] != "other"]
    print(f"Sau bỏ vai trò 'other': {len(df)}")

    records = []
    for i, r in enumerate(df.itertuples(index=False)):
        years = min_years_from_text(r.description)
        level = seniority_from_title(r.title)
        if years is None:
            years = SENIORITY_YEARS.get(level, 1)
        if level is None:
            level = years_to_seniority(years)
        records.append({
            "job_id": f"J{i:05d}",
            "title": r.title,
            "company": r.company,
            "city": r.city,
            "site": r.site,
            "role": r.role,
            "seniority": level,
            "min_years": years,
            "skills": r.skills,
            "lang": detect_lang(r.description),
            "description": r.description,
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "jobs.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # từ điển kỹ năng cuối cùng + kỹ năng phổ biến theo vai trò (dùng khi sinh CV)
    role_skills = collections.defaultdict(collections.Counter)
    for rec in records:
        role_skills[rec["role"]].update(rec["skills"])
    with open(OUT_DIR / "skills_vocab.json", "w", encoding="utf-8") as f:
        json.dump({
            "skills": sorted(vocab, key=lambda s: -freq[s]),
            "freq": {s: freq[s] for s in vocab},
            "role_skills": {r: c.most_common(60) for r, c in role_skills.items()},
        }, f, ensure_ascii=False, indent=1)

    out = pd.DataFrame(records)
    print(f"\nĐã lưu {len(out)} JD, {len(vocab)} kỹ năng.")
    print(out["role"].value_counts().to_string())
    print(out["seniority"].value_counts().to_string())
    print(out["lang"].value_counts().to_string())
    print("Số kỹ năng / JD:", out["skills"].map(len).describe().round(1).to_dict())


if __name__ == "__main__":
    main()
