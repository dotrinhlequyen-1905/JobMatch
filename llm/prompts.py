"""Prompt cho 2 tác vụ: sinh CV theo spec và review nhãn cặp JD-CV."""
import json

GEN_SYSTEM = """Bạn là chuyên gia tuyển dụng IT tại Việt Nam, viết CV mẫu chân thực để làm dữ liệu huấn luyện.
Quy tắc bắt buộc:
- Mỗi kỹ năng trong "required_skills" phải xuất hiện trong CV (có thể viết biến thể thông dụng, vd ReactJS cho React).
- KHÔNG thêm kỹ năng/công nghệ kỹ thuật nào ngoài danh sách (được thêm kỹ năng mềm).
- Tổng số năm kinh nghiệm làm việc đúng bằng "years" (0 = sinh viên/mới tốt nghiệp, chỉ có dự án).
- Viết đúng ngôn ngữ "lang" (vi = tiếng Việt, thuật ngữ công nghệ giữ tiếng Anh như CV thật; en = tiếng Anh).
- Tên người, công ty là hư cấu. Không sao chép câu chữ từ JD.
- Các mục: họ tên + chức danh, mục tiêu nghề nghiệp, kỹ năng, kinh nghiệm làm việc (gạch đầu dòng có số liệu cụ thể), dự án, học vấn.
- Độ dài 180-320 từ mỗi CV.
Chỉ trả về JSON: {"cvs": [{"id": "...", "text": "..."}]}"""


def gen_user(job, specs):
    return json.dumps({
        "job": {"title": job["title"], "description": job["description"][:1200]},
        "cv_specs": [{"id": s["id"], "target_role": s["role_display"], "seniority": s["seniority"],
                      "years": s["years"], "lang": s["lang"], "required_skills": s["skills"],
                      "note": s["note"]} for s in specs],
    }, ensure_ascii=False, indent=1)


REVIEW_SYSTEM = """Bạn là chuyên viên tuyển dụng IT. Đánh giá mức độ phù hợp của từng CV với JD tương ứng.
Thang điểm:
- 2 = Phù hợp: đúng vai trò, có hầu hết kỹ năng bắt buộc, đủ hoặc gần đủ số năm kinh nghiệm -> sẽ mời phỏng vấn.
- 1 = Phù hợp một phần: cùng/gần vai trò nhưng thiếu một số kỹ năng quan trọng hoặc thiếu kinh nghiệm rõ rệt.
- 0 = Không phù hợp: khác vai trò, hoặc thiếu phần lớn kỹ năng cốt lõi.
Coi các biến thể là cùng kỹ năng (ReactJS = React, Golang = Go, Postgres = PostgreSQL...).
Chỉ trả về JSON: {"results": [{"id": "...", "label": 0|1|2, "matched_skills": [...], "missing_skills": [...], "reason": "1-2 câu tiếng Việt"}]}"""


def review_user(cases):
    return json.dumps({"cases": [{
        "id": c["id"],
        "jd": {"title": c["job"]["title"], "level": f"{c['job']['seniority']}, tối thiểu {c['job']['min_years']} năm",
               "required_skills": c["job"]["skills"], "description": c["job"]["description"][:900]},
        "cv": c["cv"]["text"],
    } for c in cases]}, ensure_ascii=False, indent=1)


REVIEW_SYSTEM_GROUPED = REVIEW_SYSTEM.replace(
    "Đánh giá mức độ phù hợp của từng CV với JD tương ứng.",
    "Dữ liệu gồm nhiều JD, mỗi JD kèm vài CV. Đánh giá mức độ phù hợp của TỪNG CV với JD chứa nó "
    "(mỗi CV đánh giá độc lập, không so sánh giữa các CV).").replace(
    '"reason": "1-2 câu tiếng Việt"', '"reason": "1 câu ngắn tiếng Việt"')


def review_user_grouped(cases):
    """Gộp các cặp cùng JD: JD chỉ gửi 1 lần -> tiết kiệm token, xem được nhiều cặp hơn mỗi request."""
    groups = {}
    for c in cases:
        g = groups.setdefault(c["job"]["job_id"], {
            "jd": {"title": c["job"]["title"],
                   "level": f"{c['job']['seniority']}, tối thiểu {c['job']['min_years']} năm",
                   "required_skills": c["job"]["skills"], "description": c["job"]["description"][:900]},
            "cvs": []})
        g["cvs"].append({"id": c["id"], "cv": c["cv"]["text"]})
    return json.dumps({"jobs": list(groups.values())}, ensure_ascii=False, indent=1)


def parse_json(text):
    """Lấy object JSON đầu tiên trong output (model hay bọc trong ```json hoặc kèm lời dẫn)."""
    if not text:
        return None
    s = text.find("{")
    e = text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None
