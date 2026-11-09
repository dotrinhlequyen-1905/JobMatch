from ..ai.skills import ROLE_DISPLAY, vocab


def meta():
    return {
        "roles": [{"value": k, "label": v[0]} for k, v in ROLE_DISPLAY.items()],
        "seniorities": ["intern", "fresher", "junior", "middle", "senior", "lead"],
        "cities": ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Bắc Ninh", "Bình Dương"],
        "skills": vocab()["skills"],
    }
