"""Từ điển kỹ năng dùng chung với pipeline dữ liệu (data_pipeline/vocab.py) để dữ liệu
lúc train và lúc chạy thật được chuẩn hóa giống hệt nhau."""

import json
import re
from functools import lru_cache

from data_pipeline import vocab as V

from ..config import ROOT_DIR

ROLE_DISPLAY = V.ROLE_DISPLAY
RELATED_ROLES = V.RELATED_ROLES
normalize_skill = V.normalize_skill
normalize_role = V.normalize_role
years_to_seniority = V.years_to_seniority
seniority_from_title = V.seniority_from_title
min_years_from_text = V.min_years_from_text
VOCAB_FILE = ROOT_DIR / "data/processed/skills_vocab.json"
CASE_SENSITIVE = {"C", "R", "Go", "Dart", "Swift", "Flow", "Realm", "Spring", "Unity", "Apache", "Excel", "BI"}
STOP_SKILLS = {
    "Database",
    "Security",
    "Monitoring",
    "CRM",
    "Microcontrollers",
    "Automation",
    "Design",
    "Testing",
    "Cloud",
    "Server",
    "Networking",
    "Mobile",
    "Web",
    "Backend",
    "Frontend",
    "Analytics",
    "Performance",
}


@lru_cache
def vocab() -> dict:
    return json.load(open(VOCAB_FILE, encoding="utf-8"))


@lru_cache
def _patterns():
    """[(regex, tên chuẩn)], sắp theo độ dài giảm dần để 'React Native' khớp trước 'React'."""
    skills = set(vocab()["skills"]) - STOP_SKILLS
    terms = {}
    for s in skills:
        terms[s] = s
        for v in V.SURFACE_VARIANTS.get(s, []):
            terms[v] = s
    for key, canon in V.ALIASES.items():
        if canon in skills and len(key) >= 4:
            terms.setdefault(key, canon)
    out = []
    for term, canon in sorted(terms.items(), key=lambda x: -len(x[0])):
        flags = 0 if canon in CASE_SENSITIVE or len(term) <= 2 else re.IGNORECASE
        out.append((re.compile("(?<![\\w.#+/])" + re.escape(term) + "(?![\\w#+])", flags), canon))
    return out


def extract_skills(text: str) -> list[str]:
    found, taken = ([], [])
    for pat, canon in _patterns():
        for m in pat.finditer(text):
            if any((a <= m.start() < b for a, b in taken)):
                continue
            taken.append((m.start(), m.end()))
            if canon not in found:
                found.append(canon)
    return found


def normalize_skill_list(items) -> list[str]:
    out = []
    for s in items:
        n = normalize_skill(str(s))
        if n and n not in out:
            out.append(n)
    return out


def guess_role(title: str, skills: list[str]) -> str:
    """Ưu tiên chức danh; nếu không rõ thì chọn vai trò có kỹ năng trùng nhiều nhất."""
    r = normalize_role(title, title)
    if r not in ("other", "software_engineer"):
        return r
    best, best_score = ("software_engineer", 0.0)
    for role, pool in vocab()["role_skills"].items():
        weights = dict(pool[:30])
        total = sum(weights.values())
        score = sum((weights.get(s, 0) for s in skills)) / total if total else 0
        if score > best_score:
            best, best_score = (role, score)
    return best
