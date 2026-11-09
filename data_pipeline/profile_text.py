"""Tạo văn bản đầu vào cho mô hình embedding từ JD / CV.

- full    : toàn bộ nội dung (JD: tiêu đề + mô tả; CV: toàn văn)
- profile : bản rút gọn chuẩn hóa, ngắn (<256 token) -> hợp với PhoBERT/bkai

Hệ thống thật cũng dùng đúng các hàm này sau khi trích xuất CV, để dữ liệu
train và dữ liệu lúc chạy thật có cùng định dạng.
"""
from data_pipeline.vocab import ROLE_DISPLAY

SENIORITY_VI = {"intern": "Thực tập sinh", "fresher": "Fresher", "junior": "Junior",
                "middle": "Middle", "senior": "Senior", "lead": "Lead"}


def jd_full(job, max_chars=2500):
    return f"{job['title']}\n{job['description'][:max_chars]}"


def jd_profile(job):
    return (f"Vị trí: {job['title']}. Nhóm: {ROLE_DISPLAY[job['role']][0]}. "
            f"Cấp bậc: {SENIORITY_VI[job['seniority']]}, yêu cầu tối thiểu {job['min_years']} năm kinh nghiệm. "
            f"Kỹ năng yêu cầu: {', '.join(job['skills'])}.")


def cv_full(cv):
    return cv["text"]


def cv_profile(cv):
    exp = "; ".join(f"{j['position']} ({j['start']}-{j['end'] or 'nay'})" for j in cv["experience"])
    return (f"Ứng viên: {cv['title']}. Cấp bậc: {SENIORITY_VI[cv['seniority']]}, "
            f"{cv['years']} năm kinh nghiệm. Kỹ năng: {', '.join(cv['skills'])}. "
            + (f"Kinh nghiệm: {exp}. " if exp else "")
            + f"Học vấn: {cv['education']['major']}.")
