"""Đặt lịch phỏng vấn: OPEN -> HELD (có hạn) -> BOOKED; chống đặt trùng bằng UPDATE có điều kiện."""

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..core.mailer import queue_email
from ..models import Application, InterviewSlot, Job, User
from ..repositories import interviews as queries
from ..schemas.interviews import CancelIn, HoldIn, ResultIn, SlotsIn
from ..services.common import audit, aware, notify, now, slot_out
from ..state_machines import transition_application
from .jobs import _own_job


def available_slots(*, app_id: int, user: User, db: Session):
    app = queries.application_for_slots(db, app_id)
    if not app or app.candidate_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn")
    slots = queries.available_for_application(db, app)
    out = []
    for s in slots:
        mine = s.application_id == app.id
        free = s.status == "OPEN" or (s.status == "HELD" and aware(s.held_until) < now())
        if free or mine:
            out.append({**slot_out(s), "mine": mine})
    return out


def hold(*, slot_id: int, body: HoldIn, user: User, db: Session):
    return slot_out(hold_slot(db, user, slot_id, body.application_id))


def confirm(*, slot_id: int, user: User, db: Session):
    return slot_out(confirm_slot(db, user, slot_id))


def job_slots(*, job_id: int, user: User, db: Session):
    job = _own_job(db, user, job_id)
    slots = queries.list_for_job(db, job)
    names = {a.id: a.candidate.full_name for a in queries.applications_for_job(db, job)}
    return [{**slot_out(s), "candidate_name": names.get(s.application_id)} for s in slots]


def add_slots(*, job_id: int, body: SlotsIn, user: User, db: Session):
    job = _own_job(db, user, job_id)
    slots = create_slots(db, user, job, body.start_at, body.end_at, body.minutes, body.location)
    db.commit()
    return [slot_out(s) for s in slots]


def cancel(*, slot_id: int, body: CancelIn, user: User, db: Session):
    slot = queries.lock_slot(db, slot_id)
    if not slot:
        raise HTTPException(404, "Không tìm thấy khung giờ")
    if user.role == "HR":
        cancel_slot(db, user, slot, body.reason)
    else:
        candidate_cancel(db, user, slot, body.reason)
    db.commit()
    return slot_out(slot)


def result(*, slot_id: int, body: ResultIn, user: User, db: Session):
    slot = queries.get_for_result(db, slot_id)
    if not slot:
        raise HTTPException(404, "Không tìm thấy khung giờ")
    record_result(db, user, slot, body.result, body.feedback)
    db.commit()
    return slot_out(slot)


def create_slots(
    db: Session, hr: User, job: Job, start: datetime, end: datetime, minutes: int, location: str | None
) -> list[InterviewSlot]:
    if job.company.owner_id != hr.id:
        raise HTTPException(404, "Không tìm thấy tin tuyển dụng")
    start, end = (aware(start), aware(end))
    if start < now():
        raise HTTPException(400, "Không thể tạo khung giờ trong quá khứ")
    if end <= start or minutes < 10:
        raise HTTPException(400, "Khoảng thời gian không hợp lệ")
    slots, t = ([], start)
    while t + timedelta(minutes=minutes) <= end:
        slots.append((t, t + timedelta(minutes=minutes)))
        t += timedelta(minutes=minutes)
    if not slots or len(slots) > 50:
        raise HTTPException(400, "Mỗi lần tạo từ 1 đến 50 khung giờ")
    overlap = queries.find_overlap(db, end, hr, start)
    if overlap:
        raise HTTPException(409, "Khoảng thời gian bị trùng với lịch phỏng vấn đã có")
    out = [InterviewSlot(job_id=job.id, hr_id=hr.id, start_at=a, end_at=b, location=location) for a, b in slots]
    queries.add_all(db, out)
    return out


def _candidate_app(db: Session, user: User, application_id: int) -> Application:
    app = queries.get_candidate_application(db, application_id)
    if not app or app.candidate_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn ứng tuyển")
    if app.status != "INTERVIEW_INVITED":
        raise HTTPException(409, "Đơn chưa được mời phỏng vấn hoặc đã đặt lịch")
    return app


def hold_slot(db: Session, user: User, slot_id: int, application_id: int) -> InterviewSlot:
    app = _candidate_app(db, user, application_id)
    slot = queries.get_for_hold(db, slot_id)
    if not slot or slot.job_id != app.job_id:
        raise HTTPException(404, "Khung giờ không thuộc tin tuyển dụng này")
    if aware(slot.start_at) <= now():
        raise HTTPException(409, "Khung giờ đã qua")
    if queries.find_candidate_overlap(db, app, slot):
        raise HTTPException(409, "Bạn đã có lịch phỏng vấn khác trùng khung giờ này")
    queries.release_previous_hold(db, app)
    stmt = queries.build_hold(app, timedelta(minutes=settings.slot_hold_minutes), slot_id, user)
    try:
        got = queries.execute_hold(db, stmt)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Đơn của bạn đang giữ một khung giờ khác")
    if not got:
        db.rollback()
        raise HTTPException(409, "Khung giờ vừa được người khác chọn, vui lòng chọn khung khác")
    db.commit()
    db.refresh(slot)
    return slot


def confirm_slot(db: Session, user: User, slot_id: int) -> InterviewSlot:
    stmt = queries.build_confirmation(slot_id, user)
    app_id = queries.execute_confirmation(db, stmt)
    if not app_id:
        db.rollback()
        raise HTTPException(409, "Hết thời gian giữ chỗ hoặc khung giờ không còn thuộc về bạn")
    app = queries.application_for_confirmation(db, app_id)
    transition_application(db, app, "INTERVIEW_SCHEDULED", user.id, "CANDIDATE", note=f"Đặt lịch slot #{slot_id}")
    slot = queries.slot_for_confirmation(db, slot_id)
    notify(
        db,
        slot.hr_id,
        "INTERVIEW",
        f"{user.full_name} đã đặt lịch phỏng vấn {slot.start_at:%d/%m %H:%M}",
        f"/hr/jobs/{slot.job_id}",
    )
    queue_email(
        db,
        user.email,
        "Xác nhận lịch phỏng vấn JobMatch",
        f"Bạn đã đặt lịch phỏng vấn tin '{app.job.title}' lúc {aware(slot.start_at):%H:%M %d/%m/%Y}"
        + (f" tại {slot.location}" if slot.location else "")
        + ". Có thể hủy hoặc đổi lịch trong mục Hồ sơ ứng tuyển.",
    )
    audit(db, user, "SLOT_BOOKED", "interview_slot", slot_id)
    db.commit()
    db.refresh(slot)
    return slot


def release_expired(db: Session) -> int:
    res = queries.release_expired(db)
    db.commit()
    return res.rowcount


def cancel_slot(db: Session, hr: User, slot: InterviewSlot, reason: str | None):
    if slot.hr_id != hr.id:
        raise HTTPException(404, "Không tìm thấy khung giờ")
    if slot.status == "BOOKED" and slot.application_id:
        app = queries.application_for_cancellation(db, slot)
        if app.status == "INTERVIEW_SCHEDULED":
            transition_application(db, app, "INTERVIEW_INVITED", hr.id, "HR", note=f"HR hủy lịch: {reason or ''}")
        notify(
            db,
            app.candidate_id,
            "INTERVIEW",
            "Lịch phỏng vấn của bạn đã bị hủy, vui lòng chọn lại",
            "/candidate/applications",
        )
    slot.status, slot.held_by, slot.held_until, slot.application_id = ("CANCELLED", None, None, None)


def candidate_cancel(db: Session, user: User, slot: InterviewSlot, reason: str | None):
    """Ứng viên hủy chỗ đang giữ hoặc lịch đã đặt; khung giờ trở lại OPEN để người khác chọn.

    Đổi lịch = hủy rồi giữ/đặt khung giờ khác. Lịch đã đặt chỉ hủy được trước giờ phỏng vấn
    ít nhất `interview_cancel_min_hours` giờ."""
    app = queries.application_for_cancellation(db, slot) if slot.application_id else None
    if not app or app.candidate_id != user.id or slot.status not in ("HELD", "BOOKED"):
        raise HTTPException(404, "Không tìm thấy lịch của bạn")
    if slot.status == "BOOKED":
        if aware(slot.start_at) - now() < timedelta(hours=settings.interview_cancel_min_hours):
            raise HTTPException(
                409, f"Chỉ được hủy/đổi lịch trước giờ phỏng vấn ít nhất {settings.interview_cancel_min_hours} giờ"
            )
        if app.status == "INTERVIEW_SCHEDULED":
            transition_application(
                db, app, "INTERVIEW_INVITED", user.id, "CANDIDATE", note=f"Ứng viên hủy lịch: {reason or ''}".strip()
            )
        notify(
            db,
            slot.hr_id,
            "INTERVIEW",
            f"{user.full_name} đã hủy lịch phỏng vấn {aware(slot.start_at):%d/%m %H:%M}",
            f"/hr/jobs/{slot.job_id}",
        )
        hr = queries.get_user(db, slot.hr_id)
        queue_email(
            db,
            hr.email,
            "Ứng viên hủy lịch phỏng vấn",
            f"{user.full_name} đã hủy lịch phỏng vấn lúc {aware(slot.start_at):%H:%M %d/%m/%Y} "
            f"cho tin '{app.job.title}'. Lý do: {reason or 'không ghi'}. Khung giờ đã được mở lại.",
        )
    slot.status, slot.held_by, slot.held_until, slot.application_id = ("OPEN", None, None, None)
    slot.reminder_sent_at = None
    audit(db, user, "SLOT_CANCELLED_BY_CANDIDATE", "interview_slot", slot.id, {"reason": reason})


def send_reminders(db: Session) -> int:
    """Nhắc lịch cho ứng viên và nhà tuyển dụng trước buổi phỏng vấn (FR-6.5)."""
    sent = 0
    until = now() + timedelta(hours=settings.interview_reminder_hours)
    for slot_id in queries.due_reminders(db, until):
        if queries.claim_reminder(db, slot_id).rowcount != 1:
            db.rollback()
            continue
        slot = queries.get_slot(db, slot_id)
        app = queries.application_for_result(db, slot)
        hr = queries.get_user(db, slot.hr_id)
        when = f"{aware(slot.start_at):%H:%M %d/%m/%Y}"
        place = f" tại {slot.location}" if slot.location else ""
        for person, link in ((app.candidate, "/candidate/applications"), (hr, f"/hr/jobs/{slot.job_id}")):
            notify(db, person.id, "INTERVIEW", f"Nhắc lịch: phỏng vấn '{app.job.title}' lúc {when}{place}", link)
            queue_email(
                db,
                person.email,
                "Nhắc lịch phỏng vấn JobMatch",
                f"Chào {person.full_name},\n\nBuổi phỏng vấn cho tin '{app.job.title}' "
                f"(ứng viên {app.candidate.full_name}) diễn ra lúc {when}{place}.",
            )
        db.commit()
        sent += 1
    return sent


def record_result(db: Session, hr: User, slot: InterviewSlot, result: str, feedback: str | None):
    if slot.hr_id != hr.id or slot.status != "BOOKED" or (not slot.application_id):
        raise HTTPException(409, "Chỉ ghi kết quả cho lịch đã đặt")
    if result not in ("PASS", "FAIL"):
        raise HTTPException(400, "Kết quả phải là PASS hoặc FAIL")
    slot.result, slot.feedback = (result, feedback)
    app = queries.application_for_result(db, slot)
    if app.status == "INTERVIEW_SCHEDULED":
        transition_application(db, app, "INTERVIEWED", hr.id, "HR", note=f"Kết quả phỏng vấn: {result}")
