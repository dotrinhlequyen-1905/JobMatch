"""Bước 2: sinh CV tổng hợp bằng template -> data/processed/cvs.jsonl, pairs.jsonl

Mỗi JD sinh 3 CV có nhãn biết trước:
  fit       (2): cùng vai trò, có 80-100% kỹ năng JD, đủ số năm kinh nghiệm
  partial   (1): thiếu nhiều kỹ năng (partial_skill) HOẶC thiếu 2-3 năm KN (partial_senior)
  hard_neg  (0): vai trò khác hẳn, chỉ trùng vài kỹ năng chung (Git, Docker...)
"""
import json
import math
import random
import re
import unicodedata
from pathlib import Path

from data_pipeline import templates as T
from data_pipeline.vocab import RELATED_ROLES, ROLE_DISPLAY, SURFACE_VARIANTS, years_to_seniority

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
SEED = 42
P_VIETNAMESE = 0.55
P_IMPLICIT = 0.2           # tỉ lệ kỹ năng chỉ xuất hiện trong phần kinh nghiệm
CURRENT_YEAR = 2026
LABEL = {"fit": 2, "partial_skill": 1, "partial_senior": 1, "hard_neg": 0}

PROG_LANGS = {"Java", "Python", "JavaScript", "TypeScript", "C#", "C++", "C", "C/C++", "Go", "PHP",
              "Kotlin", "Swift", "Dart", "Ruby", "Rust", "Scala", "Objective-C", "SQL", "Solidity",
              "Bash", "PL/SQL", "VB.NET", "R", "Lua"}
GENERIC = {"Git", "Agile/Scrum", "Jira", "Docker", "Linux", "SQL", "CI/CD", "RESTful API",
           "Confluence", "Postman", "MySQL", "Python", "JavaScript"}

rng = random.Random(SEED)
CORE = {}   # role -> kỹ năng tiêu biểu (top 25 theo tần suất); gán trong main()


# ---------------------------------------------------------------------------
def weighted_sample(pool, k, exclude=()):
    """Lấy k kỹ năng không trùng từ pool [(skill, count), ...] theo trọng số tần suất."""
    cand = [(s, c) for s, c in pool if s not in exclude]
    out = []
    while cand and len(out) < k:
        s = rng.choices([s for s, _ in cand], weights=[c for _, c in cand])[0]
        out.append(s)
        cand = [(x, c) for x, c in cand if x != s]
    return out


def surface(skill):
    return rng.choice(SURFACE_VARIANTS.get(skill, [skill]))


def join_skills(skills, lang):
    names = [surface(s) for s in skills]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + (" và " if lang == "vi" else " and ") + names[-1]


def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def upper_first(s):
    return s[:1].upper() + s[1:]


def pick(pair, lang):
    return pair[0] if lang == "vi" else pair[1]


# ---------------------------------------------------------------------------
# Chọn kỹ năng / số năm cho từng loại CV
# ---------------------------------------------------------------------------
def plan_cv(job, kind, role_pools, roles):
    jd = job["skills"]
    role, years = job["role"], job["min_years"]

    if kind == "fit":
        k = max(1, math.ceil(len(jd) * rng.uniform(0.8, 1.0)))
        skills = rng.sample(jd, k) + weighted_sample(role_pools[role], rng.randint(1, 3), exclude=jd)
        cv_years = years + rng.randint(0, 2)
    elif kind == "partial_skill":
        # độ khớp 40-66%: đủ để "phù hợp một phần" nhưng dưới ngưỡng 70% của "phù hợp"
        lo, hi = math.ceil(len(jd) * 0.4), max(1, math.floor(len(jd) * 0.66))
        k = min(max(lo, round(len(jd) * rng.uniform(0.4, 0.6))), hi)
        skills = rng.sample(jd, k) + weighted_sample(role_pools[role], rng.randint(2, 4), exclude=jd)
        cv_years = years + rng.randint(0, 2)
    elif kind == "partial_senior":
        k = max(1, math.ceil(len(jd) * rng.uniform(0.75, 1.0)))
        skills = rng.sample(jd, k) + weighted_sample(role_pools[role], rng.randint(0, 2), exclude=jd)
        cv_years = max(0, years - rng.randint(2, 3))
    else:  # hard_neg
        banned = {role, "software_engineer"} | RELATED_ROLES.get(role, set())
        role = rng.choice([r for r in roles if r not in banned])
        own = weighted_sample(role_pools[role][:40], rng.randint(5, 8), exclude=jd)
        shared = [s for s in jd if s in GENERIC]
        skills = own + rng.sample(shared, min(len(shared), rng.randint(0, 2)))
        cv_years = max(0, years + rng.randint(-1, 1))

    rng.shuffle(skills)
    return role, skills, cv_years


# ---------------------------------------------------------------------------
# Render CV
# ---------------------------------------------------------------------------
def make_title(role, level, skills, lang):
    base = pick(ROLE_DISPLAY[role], lang)
    langs = [s for s in skills if s in PROG_LANGS - {"SQL", "Bash"}]
    if role in {"backend", "frontend", "fullstack", "mobile", "software_engineer"} and langs and rng.random() < 0.3:
        base = f"{langs[0]} Developer"
    prefix = pick(T.TITLE_PREFIX[level], lang)
    if not prefix:
        return base
    if lang == "vi" and not base.endswith("Developer"):
        return f"{base} ({prefix})"
    return f"{prefix} {base}"



def make_company(lang):
    tpl = rng.choice(T.COMPANY_SUFFIX_VI if lang == "vi" else T.COMPANY_SUFFIX_EN)
    return tpl.format(x=rng.choice(T.COMPANY_PARTS))


def fill(tpl, lang, skills, domain):
    out = tpl.format(s=join_skills(skills, lang) if skills else "", d=pick(domain, lang),
                      p=rng.choice([15, 20, 25, 30, 35, 40, 50]), n=rng.randint(3, 8))
    return re.sub(r"\ba ([aeiouAEIOU])", r"an \1", out) if lang == "en" else out


def make_experience(role, level, years, skills_for_bullets, all_skills, lang):
    if years == 0:
        return []
    n_jobs = 1 if years <= 2 else (2 if years <= 5 else rng.randint(2, 3))
    cuts = sorted(rng.sample(range(1, years), n_jobs - 1)) if n_jobs > 1 and years > n_jobs else []
    bounds = [0] + cuts + [years]
    spans = [bounds[i + 1] - bounds[i] for i in range(len(bounds) - 1)] or [years]

    # chia kỹ năng cho các công việc; công việc gần nhất nhận nhiều hơn
    chunks = [[] for _ in spans]
    for i, s in enumerate(skills_for_bullets):
        chunks[0 if rng.random() < 0.6 else i % len(spans)].append(s)

    jobs, end = [], CURRENT_YEAR
    for idx, (span, chunk) in enumerate(zip(spans, chunks)):
        start = end - max(span, 1)
        domain = rng.choice(T.DOMAINS)
        acts = rng.sample(T.ROLE_ACTIVITIES[role], min(len(T.ROLE_ACTIVITIES[role]), rng.randint(1, 3)))
        # câu đặc thù vai trò chỉ ghép kỹ năng tiêu biểu của vai trò (tránh "wireframe bằng Java");
        # kỹ năng còn lại đưa vào câu chung chung
        core_rest = [s for s in chunk if s in CORE[role]]
        rest = [s for s in chunk if s not in CORE[role]]
        core_all = [s for s in all_skills if s in CORE[role]]
        bullets = []
        for act in acts:
            tpl = pick(act, lang)
            if "{s}" in tpl:
                n = rng.randint(1, 2)
                take, core_rest = core_rest[:n], core_rest[n:]
                take = take or ([rng.choice(core_all)] if core_all else [])
                if take:
                    bullets.append(fill(tpl, lang, take, domain))
            else:
                bullets.append(fill(tpl, lang, [], domain))
        rest += core_rest
        if rest:
            bullets.append(fill(pick(rng.choice(T.GENERIC_BULLETS[3:]), lang), lang, rest, domain))
        if rng.random() < 0.5:
            bullets.append(pick(rng.choice(T.GENERIC_BULLETS[:3]), lang))
        if idx == 0 and level in {"senior", "lead"}:
            bullets.append(fill(pick(rng.choice(T.SENIOR_BULLETS), lang), lang, [], domain))
        jobs.append({
            "company": make_company(lang),
            "position": make_title(role, years_to_seniority(years - (CURRENT_YEAR - end)), chunk, lang),
            "start": start,
            "end": None if idx == 0 else end,
            "bullets": [upper_first(b) for b in bullets if b],
        })
        end = start
    return jobs


def make_projects(role, skills, lang, n):
    projects = []
    for _ in range(n):
        domain = rng.choice(T.DOMAINS)
        tech = rng.sample(skills, min(len(skills), rng.randint(2, 4)))
        act = rng.choice(T.ROLE_ACTIVITIES[role])
        desc_skills = [s for s in tech if s in CORE[role]][:2]
        if not desc_skills:   # không có kỹ năng tiêu biểu -> dùng câu mẫu không chứa {s}
            act = next((a for a in T.ROLE_ACTIVITIES[role] if "{s}" not in a[0]), T.GENERIC_BULLETS[0])
        projects.append({
            "name": upper_first(fill(pick(rng.choice(T.PROJECT_NAMES), lang), lang, [], domain)),
            "tech": [surface(s) for s in tech],
            "description": fill(pick(act, lang), lang, desc_skills, domain),
        })
    return projects


def make_cv(cv_id, role, skills, years, lang, city):
    level = years_to_seniority(years) if years > 0 else rng.choice(["intern", "fresher"])
    surname, middle, given = rng.choice(T.SURNAMES), rng.choice(T.MIDDLE), rng.choice(T.GIVEN)
    name = f"{surname} {middle} {given}"
    email = f"{strip_accents(given).lower()}.{strip_accents(surname).lower()}{rng.randint(90, 2005)}@gmail.com"
    phone = "0" + rng.choice(["9", "3", "8", "7"]) + "".join(str(rng.randint(0, 9)) for _ in range(8))
    title = make_title(role, level, skills, lang)

    implicit = [s for s in skills if rng.random() < P_IMPLICIT] if years > 0 else []
    listed = [s for s in skills if s not in implicit]
    bullet_skills = implicit + rng.sample(listed, min(len(listed), rng.randint(2, 5)))

    experience = make_experience(role, level, years, bullet_skills, skills, lang)
    projects = make_projects(role, skills, lang, 2 if years <= 1 else rng.randint(0, 2))

    top = rng.sample(listed, min(len(listed), 3)) or skills[:3]
    summ_pool = T.SUMMARY_NEWBIE if years == 0 else T.SUMMARY
    summary = pick(rng.choice(summ_pool), lang).format(
        title=pick(ROLE_DISPLAY[role], lang), y=years, s=join_skills(top, lang)).replace(" 1 years", " 1 year")

    major = rng.choice(T.MAJORS.get(role, T.MAJORS["default"]))
    grad = CURRENT_YEAR - years - rng.randint(0, 1)
    education = {"school": T.UNIVERSITIES[rng.randrange(len(T.UNIVERSITIES))], "major": pick(major, lang),
                 "start": grad - 4, "end": grad if grad <= CURRENT_YEAR else None,
                 "gpa": round(rng.uniform(2.6, 3.8), 2)}

    certs = [T.CERTS[s] for s in skills if s in T.CERTS and rng.random() < 0.35]
    if role in T.ROLE_CERTS and rng.random() < 0.5:
        certs.append(T.ROLE_CERTS[role])
    if rng.random() < 0.5:
        certs.append(rng.choice(T.LANG_CERTS))

    cv = {"cv_id": cv_id, "lang": lang, "name": name, "email": email, "phone": phone, "city": city,
          "title": title, "role": role, "seniority": level, "years": years,
          "skills": skills, "listed_skills": [surface(s) for s in listed],
          "summary": summary, "experience": experience, "projects": projects,
          "education": education, "certs": certs}
    cv["text"] = render_text(cv)
    return cv


def render_skills(cv):
    lang, listed = cv["lang"], cv["listed_skills"]
    style = rng.randint(0, 2)
    if style == 0:
        return ", ".join(listed)
    if style == 1:
        pl = [s for s in listed if s in PROG_LANGS]
        other = [s for s in listed if s not in PROG_LANGS]
        lines = []
        if pl:
            lines.append(("- Ngôn ngữ lập trình: " if lang == "vi" else "- Languages: ") + ", ".join(pl))
        if other:
            lines.append(("- Công nghệ/Công cụ: " if lang == "vi" else "- Technologies/Tools: ") + ", ".join(other))
        return "\n".join(lines)
    levels = ("Thành thạo", "Khá", "Cơ bản") if lang == "vi" else ("Advanced", "Intermediate", "Basic")
    return "\n".join(f"- {s}: {rng.choice(levels)}" for s in listed)


def render_text(cv):
    lang = cv["lang"]
    now = "Hiện tại" if lang == "vi" else "Present"
    parts = {
        "summary": cv["summary"],
        "skills": render_skills(cv),
        "experience": "\n\n".join(
            f"{j['position']} | {j['company']} | {j['start']} - {j['end'] or now}\n" +
            "\n".join(f"- {b}" for b in j["bullets"]) for j in cv["experience"]),
        "projects": "\n\n".join(
            f"{p['name']}\n" + ("Công nghệ: " if lang == "vi" else "Tech stack: ") + ", ".join(p["tech"]) +
            f"\n- {p['description']}" for p in cv["projects"]),
        "education": (f"{cv['education']['school']} | {cv['education']['major']} | "
                      f"{cv['education']['start']} - {cv['education']['end'] or now} | GPA {cv['education']['gpa']}/4"),
        "certs": "\n".join(f"- {c}" for c in cv["certs"]),
    }
    order = ["summary", "skills", "experience", "projects", "education", "certs"]
    if cv["years"] <= 1:                       # sinh viên/fresher thường để học vấn lên trước
        order = ["summary", "education", "skills", "projects", "experience", "certs"]
    elif rng.random() < 0.3:
        order = ["summary", "experience", "skills", "projects", "education", "certs"]
    header = f"{cv['name'].upper()}\n{cv['title']}\n{cv['email']} | {cv['phone']} | {cv['city']}"
    body = [f"{pick(T.SECTION_TITLES[k], lang)}\n{parts[k]}" for k in order if parts[k].strip()]
    return header + "\n\n" + "\n\n".join(body)


# ---------------------------------------------------------------------------
def main():
    jobs = [json.loads(l) for l in open(PROC / "jobs.jsonl", encoding="utf-8")]
    vocab = json.load(open(PROC / "skills_vocab.json", encoding="utf-8"))
    role_pools = {r: [tuple(x) for x in v] for r, v in vocab["role_skills"].items()}
    roles = sorted(role_pools)
    CORE.update({r: {s for s, _ in pool[:25]} for r, pool in role_pools.items()})

    cvs, pairs = [], []
    for job in jobs:
        partial_kind = "partial_senior" if job["min_years"] >= 2 and rng.random() < 0.4 else "partial_skill"
        for kind in ("fit", partial_kind, "hard_neg"):
            role, skills, years = plan_cv(job, kind, role_pools, roles)
            lang = "vi" if rng.random() < P_VIETNAMESE else "en"
            city = job["city"] if job["city"] != "Not Specified" and rng.random() < 0.7 else rng.choice(
                ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng"])
            cv = make_cv(f"C{len(cvs):05d}", role, skills, years, lang, city)
            cvs.append(cv)
            jd_set = set(job["skills"])
            pairs.append({
                "job_id": job["job_id"], "cv_id": cv["cv_id"], "kind": kind, "label": LABEL[kind],
                "skill_coverage": round(len(jd_set & set(skills)) / len(jd_set), 3),
                "years_gap": years - job["min_years"],
            })

    with open(PROC / "cvs.jsonl", "w", encoding="utf-8") as f:
        for cv in cvs:
            f.write(json.dumps(cv, ensure_ascii=False) + "\n")
    with open(PROC / "pairs.jsonl", "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    import pandas as pd
    df = pd.DataFrame(pairs)
    print(f"Đã sinh {len(cvs)} CV, {len(pairs)} cặp.")
    print(df.groupby("kind").agg(n=("label", "size"), coverage=("skill_coverage", "mean"),
                                 years_gap=("years_gap", "mean")).round(2).to_string())
    lens = pd.Series([len(c["text"].split()) for c in cvs])
    print("Số từ / CV:", lens.describe().round(0).to_dict())


if __name__ == "__main__":
    main()
