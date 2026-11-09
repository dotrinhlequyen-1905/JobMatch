"""Bước 4: xuất một phần CV của tập test ra PDF/DOCX -> data/cv_files/

Dùng để kiểm thử module trích xuất CV (PDF/DOCX -> kỹ năng, số năm KN...).
Mỗi file có đáp án trong data/cv_files/ground_truth.jsonl.
Bố cục: pdf_single (1 cột), pdf_two_col (cột trái kỹ năng/học vấn), docx.
"""
import json
import random
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from data_pipeline import templates as T

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/cv_files"
N_FILES = 200
SEED = 7
FONTS = {"Arial": ("arial.ttf", "arialbd.ttf"), "Times": ("times.ttf", "timesbd.ttf"),
         "Calibri": ("calibri.ttf", "calibrib.ttf")}
ACCENTS = ["#1F4E79", "#2E7D32", "#8E24AA", "#C62828", "#37474F"]

for name, (reg, bold) in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, f"C:/Windows/Fonts/{reg}"))
    pdfmetrics.registerFont(TTFont(f"{name}-Bold", f"C:/Windows/Fonts/{bold}"))
    addMapping(name, 0, 0, name)
    addMapping(name, 1, 0, f"{name}-Bold")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sections(cv):
    """Trả về [(tiêu đề mục, [dòng...])] theo ngôn ngữ của CV."""
    lang = 0 if cv["lang"] == "vi" else 1
    now = ("Hiện tại", "Present")[lang]
    exp = []
    for j in cv["experience"]:
        exp.append(f"<b>{esc(j['position'])}</b> — {esc(j['company'])} ({j['start']} - {j['end'] or now})")
        exp += [f"• {esc(b)}" for b in j["bullets"]]
    proj = []
    for p in cv["projects"]:
        proj.append(f"<b>{esc(p['name'])}</b> — {esc(', '.join(p['tech']))}")
        proj.append(f"• {esc(p['description'])}")
    e = cv["education"]
    return {
        "summary": (T.SECTION_TITLES["summary"][lang], [esc(cv["summary"])]),
        "skills": (T.SECTION_TITLES["skills"][lang], [esc(s) for s in cv["listed_skills"]]),
        "experience": (T.SECTION_TITLES["experience"][lang], exp),
        "projects": (T.SECTION_TITLES["projects"][lang], proj),
        "education": (T.SECTION_TITLES["education"][lang],
                      [f"<b>{esc(e['school'])}</b>", f"{esc(e['major'])} ({e['start']} - {e['end'] or now})",
                       f"GPA: {e['gpa']}/4"]),
        "certs": (T.SECTION_TITLES["certs"][lang], [f"• {esc(c)}" for c in cv["certs"]]),
    }


def pdf(cv, path, layout, rng):
    font = rng.choice(list(FONTS))
    accent = colors.HexColor(rng.choice(ACCENTS))
    st = {
        "name": ParagraphStyle("n", fontName=f"{font}-Bold", fontSize=20, leading=24, textColor=accent),
        "title": ParagraphStyle("t", fontName=font, fontSize=12, leading=16),
        "h": ParagraphStyle("h", fontName=f"{font}-Bold", fontSize=11.5, leading=15, textColor=accent,
                            spaceBefore=8, spaceAfter=3),
        "p": ParagraphStyle("p", fontName=font, fontSize=9.5, leading=13),
    }
    sec = sections(cv)
    head = [Paragraph(esc(cv["name"].upper()), st["name"]), Paragraph(esc(cv["title"]), st["title"]),
            Paragraph(f"{cv['email']} | {cv['phone']} | {esc(cv['city'])}", st["p"]), Spacer(1, 6)]

    def block(key, skills_inline=True):
        title, lines = sec[key]
        if not lines:
            return []
        if key == "skills" and skills_inline:
            lines = [", ".join(lines)]
        return [Paragraph(title, st["h"])] + [Paragraph(l, st["p"]) for l in lines]

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=cv["name"])
    if layout == "pdf_single":
        order = ["summary", "skills", "experience", "projects", "education", "certs"]
        if cv["years"] <= 1:
            order = ["summary", "education", "skills", "projects", "experience", "certs"]
        story = head + [f for k in order for f in block(k)]
    else:
        left = [f for k in ("skills", "education", "certs") for f in block(k, skills_inline=False)]
        right = [f for k in ("summary", "experience", "projects") for f in block(k)]
        table = Table([[left, right]], colWidths=[58 * mm, 122 * mm])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F2F4F7")),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        story = head + [table]
    doc.build(story)


def docx(cv, path, rng):
    d = Document()
    style = d.styles["Normal"]
    style.font.name = rng.choice(["Arial", "Times New Roman", "Calibri"])
    style.font.size = Pt(10.5)
    color = RGBColor.from_string(rng.choice(ACCENTS)[1:])
    h = d.add_paragraph()
    r = h.add_run(cv["name"].upper())
    r.bold, r.font.size, r.font.color.rgb = True, Pt(18), color
    d.add_paragraph(cv["title"])
    d.add_paragraph(f"{cv['email']} | {cv['phone']} | {cv['city']}")
    for key, (title, lines) in sections(cv).items():
        if not lines:
            continue
        p = d.add_paragraph()
        r = p.add_run(title)
        r.bold, r.font.color.rgb = True, color
        if key == "skills":
            lines = [", ".join(lines)]
        for l in lines:
            clean = l.replace("<b>", "").replace("</b>", "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            d.add_paragraph(clean.lstrip("• "), style="List Bullet" if l.startswith("•") else None)
    d.save(str(path))


def main():
    rng = random.Random(SEED)
    cvs = [json.loads(l) for l in open(ROOT / "data/final/cvs.jsonl", encoding="utf-8")]
    test = [c for c in cvs if c["split"] == "test"]
    chosen = rng.sample(test, min(N_FILES, len(test)))
    OUT.mkdir(parents=True, exist_ok=True)
    truth = []
    for i, cv in enumerate(chosen):
        layout = ["pdf_single", "pdf_two_col", "docx"][i % 3]
        path = OUT / f"{cv['cv_id']}.{'docx' if layout == 'docx' else 'pdf'}"
        if layout == "docx":
            docx(cv, path, rng)
        else:
            pdf(cv, path, layout, rng)
        truth.append({"file": path.name, "cv_id": cv["cv_id"], "layout": layout, "lang": cv["lang"],
                      "name": cv["name"], "email": cv["email"], "phone": cv["phone"],
                      "skills": cv["skills"], "years": cv["years"], "role": cv["role"],
                      "seniority": cv["seniority"], "education": cv["education"]})
    with open(OUT / "ground_truth.jsonl", "w", encoding="utf-8") as f:
        for t in truth:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Đã xuất {len(truth)} file vào {OUT}")


if __name__ == "__main__":
    main()
