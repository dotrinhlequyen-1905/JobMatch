"""Trích xuất thông tin từ CV phi cấu trúc (PDF/DOCX/TXT)."""

import io
import re
from datetime import datetime

from .skills import extract_skills, guess_role, years_to_seniority

SECTION_HEADERS = {
    "summary": "mục tiêu|giới thiệu|summary|objective|profile|about",
    "skills": "kỹ năng|skills?|technical skills|công nghệ",
    "experience": "kinh nghiệm|experience|employment|work history|quá trình làm việc",
    "projects": "dự án|projects?",
    "education": "học vấn|education|trình độ",
    "certs": "chứng chỉ|certifications?|certificates?",
}
EMAIL_RE = re.compile("[\\w.+-]+@[\\w-]+\\.[\\w.]+")
PHONE_RE = re.compile("(?:\\+?84|0)(?:[\\s.-]?\\d){9,10}")
RANGE_RE = re.compile(
    "((?:\\d{1,2}/)?(?:19|20)\\d{2})\\s*[-–—~]\\s*((?:\\d{1,2}/)?(?:19|20)\\d{2}|hiện tại|nay|present|now|current)",
    re.IGNORECASE,
)
YEARS_RE = re.compile("(\\d{1,2})\\+?\\s*(?:năm|years?)\\s*(?:kinh nghiệm|of experience|experience)?", re.IGNORECASE)


def read_file(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pymupdf

        with pymupdf.open(stream=data, filetype="pdf") as doc:
            return "\n".join((page.get_text() for page in doc))
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join((c.text for c in row.cells)))
        return "\n".join(parts)
    return data.decode("utf-8", errors="ignore")


def split_sections(text: str) -> dict[str, str]:
    """Tách mục dựa trên các dòng tiêu đề ngắn (vd 'KINH NGHIỆM LÀM VIỆC', 'Skills:')."""
    sections, current = ({"header": []}, "header")
    for line in text.splitlines():
        stripped = line.strip().rstrip(":").strip()
        key = None
        if 0 < len(stripped) <= 40 and (not re.search("\\d", stripped)):
            for k, pat in SECTION_HEADERS.items():
                if re.fullmatch(f"(?:\\w+\\s+){{0,2}}(?:{pat})(?:\\s+\\w+){{0,3}}", stripped, re.IGNORECASE):
                    key = k
                    break
        if key:
            current = key
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _year(tok: str, now: int) -> int:
    if re.fullmatch("hiện tại|nay|present|now|current", tok, re.IGNORECASE):
        return now
    return int(tok[-4:])


def estimate_years(sections: dict[str, str], full: str) -> int:
    """Tổng số năm từ các khoảng thời gian trong mục kinh nghiệm (gộp khoảng chồng nhau)."""
    now = datetime.now().year
    src = sections.get("experience") or ""
    spans = sorted(((_year(a, now), _year(b, now)) for a, b in RANGE_RE.findall(src)))
    spans = [(a, b) for a, b in spans if 1980 < a <= b <= now]
    total, cur = (0, None)
    for a, b in spans:
        if cur and a <= cur[1]:
            cur = (cur[0], max(cur[1], b))
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = (a, b)
    if cur:
        total += cur[1] - cur[0]
    if total:
        return total
    m = YEARS_RE.search(sections.get("summary", "") + "\n" + full[:1500])
    return int(m.group(1)) if m and int(m.group(1)) <= 40 else 0


def parse_cv_text(text: str) -> dict:
    sections = split_sections(text)
    header_lines = [line.strip() for line in sections.get("header", "").splitlines() if line.strip()]
    name = header_lines[0].title() if header_lines else ""
    title = header_lines[1] if len(header_lines) > 1 and "@" not in header_lines[1] else ""
    email = (EMAIL_RE.search(text) or [None])[0]
    phone_m = PHONE_RE.search(text)
    skills = extract_skills(text)
    years = estimate_years(sections, text)
    role = guess_role(title, skills)
    return {
        "name": name,
        "title": title,
        "email": email,
        "phone": re.sub("[\\s.-]", "", phone_m.group(0)) if phone_m else None,
        "skills": skills,
        "years": years,
        "seniority": years_to_seniority(years) if years else "fresher",
        "role": role,
        "experience": extract_positions(sections.get("experience", "")),
        "major": extract_major(sections.get("education", "")),
        "sections": {k: v for k, v in sections.items() if k != "header"},
    }


def extract_positions(exp_text: str) -> list[dict]:
    """Các dòng có khoảng thời gian trong mục kinh nghiệm -> [{position, start, end}] (end=None nghĩa là hiện tại)."""
    now = datetime.now().year
    out = []
    for line in exp_text.splitlines():
        m = RANGE_RE.search(line)
        if not m:
            continue
        before = line[: m.start()].rstrip(" (").strip(" •-|")
        head = re.split("\\s[|—–]\\s|\\s-\\s", before, maxsplit=1)[0].strip(" |—–-")
        if not head or len(head) > 80:
            continue
        end = _year(m.group(2), now)
        out.append(
            {
                "position": head,
                "start": _year(m.group(1), now),
                "end": None if re.fullmatch("hiện tại|nay|present|now|current", m.group(2), re.I) else end,
            }
        )
    return out[:5]


def extract_major(edu_text: str) -> str:
    """Ngành học. Thứ tự ưu tiên: phần thứ 2 của dòng 'Trường | Ngành | năm'; dòng có khoảng năm
    (vd 'Software Engineering (2015 - 2019)'); dòng đầu tiên không phải tên trường/GPA."""
    lines = [line.strip(" •-") for line in edu_text.splitlines() if line.strip(" •-")]
    school = re.compile("trường|đại học|university|học viện|college|gpa", re.I)
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            return parts[1]
    for line in lines:
        if RANGE_RE.search(line) and (not school.search(line)):
            return RANGE_RE.sub("", line).strip(" ()")
    return next((line for line in lines if not school.search(line)), "")


def parse_cv_file(data: bytes, filename: str) -> dict:
    text = read_file(data, filename)
    return {"raw_text": text, **parse_cv_text(text)}
