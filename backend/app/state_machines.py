"""Máy trạng thái: đơn ứng tuyển và đơn hàng.

Mọi chuyển trạng thái đều đi qua bảng TRANSITIONS; cập nhật dùng
`UPDATE ... WHERE status = <trạng thái cũ>` nên hai thao tác đồng thời không thể
cùng thành công (optimistic concurrency).
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Application
from .repositories import state_machines as queries

APP_STATUSES = [
    "NEW",
    "SCREENING",
    "INTERVIEW_INVITED",
    "INTERVIEW_SCHEDULED",
    "INTERVIEWED",
    "OFFERED",
    "REJECTED",
    "WITHDRAWN",
]
APP_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "NEW": {"SCREENING": {"HR"}, "REJECTED": {"HR"}, "WITHDRAWN": {"CANDIDATE"}},
    "SCREENING": {"INTERVIEW_INVITED": {"HR"}, "REJECTED": {"HR"}, "WITHDRAWN": {"CANDIDATE"}},
    "INTERVIEW_INVITED": {
        "INTERVIEW_SCHEDULED": {"CANDIDATE", "SYSTEM"},
        "REJECTED": {"HR"},
        "WITHDRAWN": {"CANDIDATE"},
    },
    "INTERVIEW_SCHEDULED": {
        "INTERVIEWED": {"HR"},
        "INTERVIEW_INVITED": {"HR", "CANDIDATE", "SYSTEM"},
        "REJECTED": {"HR"},
        "WITHDRAWN": {"CANDIDATE"},
    },
    "INTERVIEWED": {"OFFERED": {"HR"}, "REJECTED": {"HR"}},
    "OFFERED": {},
    "REJECTED": {},
    "WITHDRAWN": {},
}
APP_STATUS_VI = {
    "NEW": "Đã nộp",
    "SCREENING": "Đang sàng lọc",
    "INTERVIEW_INVITED": "Mời phỏng vấn",
    "INTERVIEW_SCHEDULED": "Đã đặt lịch phỏng vấn",
    "INTERVIEWED": "Đã phỏng vấn",
    "OFFERED": "Trúng tuyển",
    "REJECTED": "Không phù hợp",
    "WITHDRAWN": "Đã rút đơn",
}
APP_TRANSITIONS["INTERVIEWED"]["WITHDRAWN"] = {"CANDIDATE"}


def allowed_next(status: str, role: str) -> list[str]:
    return [to for to, roles in APP_TRANSITIONS.get(status, {}).items() if role in roles]


def transition_application(
    db: Session, app: Application, to: str, actor_id: int | None, actor_role: str, note: str | None = None
) -> Application:
    """Chuyển trạng thái đơn. Gọi trong transaction của request; commit do nơi gọi."""
    frm = app.status
    if to not in APP_TRANSITIONS.get(frm, {}):
        raise HTTPException(409, f"Không thể chuyển từ {APP_STATUS_VI.get(frm, frm)} sang {APP_STATUS_VI.get(to, to)}")
    if actor_role not in APP_TRANSITIONS[frm][to]:
        raise HTTPException(403, "Vai trò của bạn không được thực hiện bước chuyển này")
    res = queries.compare_and_set(db, app, frm, to)
    if res.rowcount != 1:
        raise HTTPException(409, "Đơn vừa được người khác cập nhật, vui lòng tải lại")
    queries.append_history(db, actor_id, app, frm, note, to)
    queries.append_notification(db, APP_STATUS_VI, app, to)
    db.refresh(app)
    return app


ORDER_TRANSITIONS = {
    "PENDING": {"PAID", "EXPIRED", "CANCELLED", "RECONCILING"},
    "RECONCILING": {"PAID", "CANCELLED"},
    "PAID": {"REFUND_REQUESTED"},
    "REFUND_REQUESTED": {"REFUNDED", "PAID"},
    "EXPIRED": {"RECONCILING"},
    "CANCELLED": set(),
    "REFUNDED": set(),
}
