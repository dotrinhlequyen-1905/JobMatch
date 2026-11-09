"""Kiểm thử các yêu cầu được bổ sung để khớp đặc tả: FR-1.x, FR-2.4, FR-3.1/3.3/3.5, FR-6.4/6.5, FR-7.6, FR-8.5."""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core import mailer
from app.core.database import SessionLocal
from app.models import AuditLog, CVSkill, InterviewSlot, JobSkill, Order, Skill
from app.services.interviews import send_reminders
from tests.conftest import login, register
from tests.test_flows import _invited_apps, _order, _webhook, apply

API = "/api/v1"


def _token_from_last_email(to):
    mail = next(m for m in reversed(mailer.outbox) if m["to"] == to)
    return re.search(r"token=([\w-]+)", mail["body"]).group(1)


# ---------------------------------------------------------------- FR-1: tài khoản và phiên


def test_refresh_rotation_logout_and_reuse_detection(client):
    r = client.post(f"{API}/auth/register", json={"email": "s@t.vn", "password": "123456", "full_name": "Sess", "role": "CANDIDATE"})
    first = r.json()["refresh_token"]
    rotated = client.post(f"{API}/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200 and rotated.json()["token"]
    second = rotated.json()["refresh_token"]
    # Dùng lại refresh token cũ => thu hồi toàn bộ phiên (kể cả token vừa xoay vòng).
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": first}).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": second}).status_code == 401
    third = client.post(f"{API}/auth/login", json={"email": "s@t.vn", "password": "123456"}).json()["refresh_token"]
    assert client.post(f"{API}/auth/logout", json={"refresh_token": third}).status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": third}).status_code == 401


def test_forgot_and_reset_password_single_use(client, monkeypatch):
    from app.config import settings
    from app.services import auth as auth_service

    register(client, "forgot@t.vn", "CANDIDATE")
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(
        auth_service, "deliver", lambda to, subject, body: mailer.outbox.append({"to": to, "subject": subject, "body": body})
    )
    unknown = client.post(f"{API}/auth/forgot-password", json={"email": "nobody@t.vn"})
    known = client.post(f"{API}/auth/forgot-password", json={"email": "forgot@t.vn"})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()  # không lộ email đã đăng ký
    token = _token_from_last_email("forgot@t.vn")
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "password": "newpass1"}).status_code == 200
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "password": "again12"}).status_code == 400
    assert client.post(f"{API}/auth/login", json={"email": "forgot@t.vn", "password": "123456"}).status_code == 401
    login(client, "forgot@t.vn", "newpass1")


def test_email_verification(client):
    h = register(client, "verify@t.vn", "CANDIDATE")
    assert client.get(f"{API}/users/me", headers=h).json()["user"]["email_verified"] is False
    token = _token_from_last_email("verify@t.vn")
    assert client.post(f"{API}/auth/verify-email", json={"token": token}).status_code == 200
    assert client.get(f"{API}/users/me", headers=h).json()["user"]["email_verified"] is True
    assert client.post(f"{API}/auth/resend-verification", headers=h).status_code == 409


def test_change_password_requires_current_password(client):
    h = register(client, "passwd@t.vn", "CANDIDATE")
    assert client.put(f"{API}/users/me", json={"password": "abcdef"}, headers=h).status_code == 400
    assert client.put(f"{API}/users/me", json={"password": "abcdef", "current_password": "wrong"}, headers=h).status_code == 400
    r = client.put(f"{API}/users/me", json={"password": "abcdef", "current_password": "123456"}, headers=h)
    assert r.status_code == 200 and r.json()["refresh_token"]
    login(client, "passwd@t.vn", "abcdef")


def test_avatar_upload_validates_image(client):
    h = register(client, "avatar@t.vn", "CANDIDATE")
    bad = client.post(f"{API}/users/me/avatar", files={"file": ("x.png", b"not an image", "image/png")}, headers=h)
    assert bad.status_code == 400
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    ok = client.post(f"{API}/users/me/avatar", files={"file": ("x.png", png, "image/png")}, headers=h)
    assert ok.status_code == 200
    url = ok.json()["user"]["avatar_url"]
    assert client.get(url).content == png


def test_company_logo_upload_replaces_logo_url(client):
    h = register(client, "logo@t.vn", "HR", "Logo Co")
    assert client.post(f"{API}/companies/me/logo", files={"file": ("x.png", b"nope", "image/png")}, headers=h).status_code == 400
    png = b"\x89PNG\r\n\x1a\n" + b"1" * 32
    first = client.post(f"{API}/companies/me/logo", files={"file": ("x.png", png, "image/png")}, headers=h).json()["logo_url"]
    assert client.get(first).content == png
    second = client.post(f"{API}/companies/me/logo", files={"file": ("y.png", png, "image/png")}, headers=h).json()["logo_url"]
    assert client.get(f"{API}/companies/me", headers=h).json()["logo_url"] == second
    assert client.get(first).status_code == 404
    assert client.get(f"{API}/companies/logos/..%2F..%2Fapp.py").status_code == 404


def test_lock_revokes_sessions_and_denied_access_is_logged(world):
    c, admin = world["c"], world["admin"]
    refresh = c.post(f"{API}/auth/login", json={"email": "uv0@t.vn", "password": "123456"}).json()
    uid = refresh["user"]["id"]
    assert c.get(f"{API}/admin/users", headers=world["cands"][0]).status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "ACCESS_DENIED", AuditLog.actor_id == uid))
    assert c.post(f"{API}/admin/users/{uid}/status", json={"status": "LOCKED"}, headers=admin).status_code == 200
    assert c.post(f"{API}/auth/refresh", json={"refresh_token": refresh["refresh_token"]}).status_code == 401
    history = c.get(f"{API}/admin/audit-logs", params={"actor_id": uid}, headers=admin).json()
    assert {"LOGIN", "ACCESS_DENIED"} <= {a["action"] for a in history}


# ---------------------------------------------------------------- FR-2.4: hồ sơ ứng viên


def test_hidden_profile_excluded_from_hr_search(world):
    c, hr, cand = world["c"], world["hr"], world["cands"][0]
    route = f"{API}/jobs/{world['job']['id']}/candidates"
    assert len(c.get(route, headers=hr).json()) == 2
    r = c.put(f"{API}/users/me/profile", json={"headline": "Backend dev", "is_public": False}, headers=cand)
    assert r.status_code == 200 and r.json()["is_public"] is False
    assert c.get(f"{API}/users/me/profile", headers=cand).json()["headline"] == "Backend dev"
    assert len(c.get(route, headers=hr).json()) == 1


# ---------------------------------------------------------------- FR-3: tin tuyển dụng


def test_draft_submit_close_reopen_and_views(world):
    c, hr, admin = world["c"], world["hr"], world["admin"]
    body = {"title": "Python Developer", "description": "Phát triển API bằng Python, FastAPI, PostgreSQL, Docker cho hệ thống.", "submit": False}
    draft = c.post(f"{API}/jobs", json=body, headers=hr).json()
    assert draft["status"] == "DRAFT"
    path = f"{API}/jobs/{draft['id']}/status"
    assert c.patch(path, json={"status": "PENDING"}, headers=hr).json()["status"] == "PENDING"
    c.patch(f"{API}/admin/jobs/{draft['id']}/moderate", json={"status": "PUBLISHED"}, headers=admin)
    for _ in range(3):
        c.get(f"{API}/jobs/{draft['id']}")
    c.get(f"{API}/jobs/{draft['id']}", headers=hr)  # chủ tin xem không tính lượt
    assert c.patch(path, json={"status": "CLOSED"}, headers=hr).json()["status"] == "CLOSED"
    assert c.patch(path, json={"status": "CLOSED"}, headers=hr).status_code == 409
    reopened = c.patch(path, json={"status": "PENDING", "expires_in_days": 15}, headers=hr).json()
    assert reopened["status"] == "PENDING"
    mine = {j["id"]: j for j in c.get(f"{API}/jobs/owned", headers=hr).json()}
    assert mine[draft["id"]]["view_count"] == 3


def test_owned_jobs_report_average_match(world):
    apply(world, 0)
    job = next(j for j in world["c"].get(f"{API}/jobs/owned", headers=world["hr"]).json() if j["id"] == world["job"]["id"])
    assert job["applications"] == 1 and job["avg_match_score"] is not None


def test_skill_tables_follow_json_skills(world):
    c, cand = world["c"], world["cands"][0]
    cv_id = c.get(f"{API}/cvs", headers=cand).json()[0]["id"]
    c.put(f"{API}/cvs/{cv_id}", json={"skills": ["Python", "Docker"]}, headers=cand)
    with SessionLocal() as db:
        names = set(db.scalars(select(Skill.name).join(CVSkill).where(CVSkill.cv_id == cv_id)))
        assert names == {"Python", "Docker"}
        assert db.scalar(select(JobSkill).where(JobSkill.job_id == world["job"]["id"])) is not None


# ---------------------------------------------------------------- FR-4.4: gap cho HR


def test_hr_gap_only_for_applied_cv(world):
    c, hr = world["c"], world["hr"]
    cv_other = c.get(f"{API}/cvs", headers=world["cands"][1]).json()[0]["id"]
    q = {"job_id": world["job"]["id"]}
    assert c.get(f"{API}/matching/gap", params={**q, "cv_id": cv_other}, headers=hr).status_code == 403
    app = apply(world, 0)
    r = c.get(f"{API}/matching/gap", params={**q, "cv_id": app["cv"]["id"]}, headers=hr)
    assert r.status_code == 200 and "missing_skills" in r.json()["match"]


# ---------------------------------------------------------------- FR-6.4/6.5: phỏng vấn


def _book(world, app_id, slot_id, h):
    c = world["c"]
    assert c.post(f"{API}/interview-slots/{slot_id}/hold", json={"application_id": app_id}, headers=h).status_code == 200
    assert c.post(f"{API}/interview-slots/{slot_id}/book", headers=h).status_code == 200


def test_candidate_cancels_and_reschedules(world):
    apps, slots = _invited_apps(world)
    c, h0, h1 = world["c"], world["cands"][0], world["cands"][1]
    _book(world, apps[0], slots[0]["id"], h0)
    assert c.post(f"{API}/interview-slots/{slots[0]['id']}/cancel", json={}, headers=h1).status_code == 404
    r = c.post(f"{API}/interview-slots/{slots[0]['id']}/cancel", json={"reason": "Bận"}, headers=h0)
    assert r.status_code == 200 and r.json()["status"] == "OPEN"
    app = next(a for a in c.get(f"{API}/applications", headers=h0).json() if a["id"] == apps[0])
    assert app["status"] == "INTERVIEW_INVITED"
    _book(world, apps[0], slots[1]["id"], h0)  # đổi lịch sang khung khác
    _book(world, apps[1], slots[0]["id"], h1)  # khung cũ đã trống cho người khác


def test_cannot_cancel_too_close_to_interview(world):
    apps, slots = _invited_apps(world)
    _book(world, apps[0], slots[0]["id"], world["cands"][0])
    with SessionLocal() as db:
        db.get(InterviewSlot, slots[0]["id"]).start_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()
    r = world["c"].post(f"{API}/interview-slots/{slots[0]['id']}/cancel", json={}, headers=world["cands"][0])
    assert r.status_code == 409


def test_reminders_sent_once_to_both_parties(world):
    apps, slots = _invited_apps(world)
    _book(world, apps[0], slots[0]["id"], world["cands"][0])
    mailer.outbox.clear()
    with SessionLocal() as db:
        assert send_reminders(db) == 1
        assert send_reminders(db) == 0
    assert {m["to"] for m in mailer.outbox} == {"uv0@t.vn", "hr@t.vn"}


# ---------------------------------------------------------------- FR-7: đối soát


def test_reconciling_order_approved_by_admin(world):
    c, h, admin = world["c"], world["cands"][0], world["admin"]
    o = _order(c, h, "CAND")
    assert _webhook(c, "RC1", o["order_code"], o["amount"] + 5000).json()["status"] == "AMOUNT_MISMATCH"
    assert c.get(f"{API}/orders/{o['id']}", headers=h).json()["status"] == "RECONCILING"
    assert c.get(f"{API}/admin/reconcile", headers=admin).json()["reconciling_orders"] == 1
    r = c.post(f"{API}/admin/orders/{o['id']}/resolve", json={"approve": True, "note": "Khách chuyển dư"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "PAID"
    assert c.get(f"{API}/users/me", headers=h).json()["user"]["is_premium"] is True
    report = c.get(f"{API}/admin/reconcile", headers=admin).json()
    assert not any(p.get("order_code") == o["order_code"] for p in report["problems"])


def test_reconciling_order_rejected_and_unmatched_tx_assigned(world):
    c, h, admin = world["c"], world["cands"][0], world["admin"]
    o = _order(c, h, "CAND")
    _webhook(c, "RC2", "chuyen tien ghi sai noi dung", o["amount"])
    tx = c.get(f"{API}/admin/transactions", params={"status": "UNMATCHED"}, headers=admin).json()["items"][0]
    r = c.post(f"{API}/admin/transactions/{tx['id']}/assign", json={"order_code": o["order_code"]}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "RECONCILING"
    r = c.post(f"{API}/admin/orders/{o['id']}/resolve", json={"approve": False}, headers=admin)
    assert r.json()["status"] == "CANCELLED"
    report = c.get(f"{API}/admin/reconcile", headers=admin).json()
    assert any(p["type"] == "TX_REFUND_DUE" for p in report["problems"])


def test_late_payment_after_expiry_goes_to_reconciling(world):
    c, h = world["c"], world["cands"][0]
    o = _order(c, h, "CAND")
    with SessionLocal() as db:
        db.get(Order, o["id"]).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert _webhook(c, "RC3", o["order_code"], o["amount"]).json()["status"] == "LATE"
    assert c.get(f"{API}/orders/{o['id']}", headers=h).json()["status"] == "RECONCILING"


def test_reconcile_ingests_transactions_missing_from_webhooks(world, monkeypatch):
    from app.config import settings
    from app.services import payments

    c, h, admin = world["c"], world["cands"][0], world["admin"]
    o = _order(c, h, "CAND")
    monkeypatch.setattr(settings, "sepay_api_token", "test-token")
    remote = [{"id": "SP-1", "transferType": "in", "transferAmount": o["amount"], "content": f"CK {o['order_code']}"}]
    monkeypatch.setattr(payments, "fetch_sepay_transactions", lambda since: remote)
    report = c.get(f"{API}/admin/reconcile", headers=admin).json()
    assert any(p["type"] == "MISSING_WEBHOOK" and p["status"] == "MATCHED" for p in report["problems"])
    assert c.get(f"{API}/orders/{o['id']}", headers=h).json()["status"] == "PAID"
    report = c.get(f"{API}/admin/reconcile", headers=admin).json()
    assert not any(p["type"] == "MISSING_WEBHOOK" for p in report["problems"])


# ---------------------------------------------------------------- FR-8.5: báo cáo vi phạm


def test_report_flow_with_close_job_action(world):
    c, cand, admin = world["c"], world["cands"][0], world["admin"]
    body = {"target_type": "JOB", "target_id": world["job"]["id"], "reason": "Tin tuyển dụng yêu cầu đóng phí trước"}
    r = c.post(f"{API}/reports", json=body, headers=cand)
    assert r.status_code == 200 and r.json()["status"] == "OPEN"
    assert c.post(f"{API}/reports", json=body, headers=cand).status_code == 409
    rid = c.get(f"{API}/admin/reports", headers=admin).json()["items"][0]["id"]
    bad = c.post(f"{API}/admin/reports/{rid}", json={"status": "DISMISSED", "action": "CLOSE_JOB"}, headers=admin)
    assert bad.status_code == 400
    ok = c.post(f"{API}/admin/reports/{rid}", json={"status": "RESOLVED", "action": "CLOSE_JOB"}, headers=admin)
    assert ok.status_code == 200
    assert c.get(f"{API}/jobs/{world['job']['id']}").status_code == 404
    assert c.get(f"{API}/reports/mine", headers=cand).json()[0]["status"] == "RESOLVED"
    assert c.get(f"{API}/admin/stats", headers=admin).json()["open_reports"] == 0
