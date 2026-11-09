"""Evidence-based CV completeness assessment; it never invents candidate claims."""

from .matcher import skill_gap


def evaluate(cv, job=None, match=None):
    parsed = cv.parsed or {}
    sections = parsed.get("sections") or {}
    experience = parsed.get("experience") or []
    evidence = {
        "Thông tin liên hệ": bool(parsed.get("email") or parsed.get("phone")),
        "Vị trí và mục tiêu": bool(parsed.get("title")),
        "Học vấn": bool(parsed.get("major") or sections.get("education")),
        "Kinh nghiệm": bool(experience or sections.get("experience")),
        "Kỹ năng": bool(cv.skills),
        "Dự án": bool(sections.get("projects")),
        "Chứng chỉ": bool(sections.get("certs")),
    }
    weights = [15, 10, 15, 25, 20, 10, 5]
    components, strengths, suggestions = ([], [], [])
    for (name, present), weight in zip(evidence.items(), weights):
        components.append(
            {
                "name": name,
                "score": 100 if present else 0,
                "comment": "Đã nhận diện nội dung" if present else "Chưa nhận diện rõ nội dung trong CV",
            }
        )
        if present:
            strengths.append(f"CV có phần {name.lower()} được nhận diện")
        else:
            suggestions.append(
                {
                    "priority": "Cao" if weight >= 15 else "Trung bình",
                    "section": name,
                    "issue": "Bộ trích xuất chưa nhận diện nội dung này",
                    "suggestion": f"Kiểm tra cách trình bày phần {name.lower()}; chỉ bổ sung thông tin nếu bạn thực sự có.",
                }
            )
    score = sum((weight for present, weight in zip(evidence.values(), weights) if present))
    gap = skill_gap(job.skills or [], cv.skills or []) if job else {"matched": [], "missing": []}
    for skill in gap["missing"]:
        suggestions.append(
            {
                "priority": "Cao",
                "section": "Kỹ năng",
                "issue": f"Chưa thấy minh chứng về {skill}",
                "suggestion": f"Nếu đã sử dụng {skill}, hãy mô tả dự án hoặc công việc thực tế. Nếu chưa, cân nhắc học và thực hành trước khi khai báo.",
            }
        )
    return {
        "cv_id": cv.id,
        "job_id": job.id if job else None,
        "cv_score": score,
        "match_score": match["score"] if match else None,
        "match": match,
        "components": components,
        "strengths": strengths,
        "matched_skills": gap["matched"],
        "missing_skills": gap["missing"],
        "suggestions": suggestions,
        "can_apply": True,
        "method": "Đánh giá mức độ đầy đủ theo nội dung đã trích xuất; không phải dự đoán kết quả tuyển dụng.",
    }
