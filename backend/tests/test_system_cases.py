"""Ca kiểm thử hệ thống theo yêu cầu chức năng (Chương 6): bổ sung các nhánh biên và endpoint chưa được kiểm thử.

Mỗi test ghi mã ca (ST-xx) và yêu cầu liên quan để đối chiếu với bảng ca kiểm thử trong báo cáo.
"""

import io
from datetime import datetime, timedelta, timezone

from docx import Document

from app.config import settings
from app.core.database import SessionLocal
from app.models import Order
from app.services.common import now
from tests.conftest import CV_TEXT, login, register
from tests.test_flows import _order, apply, hr_move

API = "/api/v1"


# ---------------------------------------------------------------- FR-1: tài khoản và phân quyền


def test_st01_register_validates_input_and_duplicate_email(client):
    """ST-01 · FR-1.1: dữ liệu đăng ký sai bị từ chối, email trùng (không phân biệt hoa thường) bị chặn."""
    base = {"email": "dup@t.vn", "password": "123456", "full_name": "Ung Vien", "role": "CANDIDATE"}
    assert client.post(f"{API}/auth/register", json={**base, "email": "khong-phai-email"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={**base, "password": "123"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={**base, "role": "ADMIN"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={**base, "role": "HR"}).status_code == 400
    assert client.post(f"{API}/auth/register", json=base).status_code == 200
    assert client.post(f"{API}/auth/register", json={**base, "email": "DUP@t.vn"}).status_code == 409


def test_st02_login_rejects_wrong_password_and_locked_account(client):
    """ST-02 · FR-1.2, FR-1.6: sai mật khẩu trả 401; tài khoản bị khóa không đăng nhập được, mở khóa thì được."""
    register(client, "login@t.vn", "CANDIDATE")
    assert client.post(f"{API}/auth/login", json={"email": "login@t.vn", "password": "sai-mat-khau"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "khongco@t.vn", "password": "123456"}).status_code == 401
    admin = login(client, "admin@t.vn")
    uid = client.get(f"{API}/users/me", headers=login(client, "login@t.vn")).json()["user"]["id"]
    assert client.post(f"{API}/admin/users/{uid}/status", json={"status": "LOCKED"}, headers=admin).status_code == 200
    assert client.post(f"{API}/auth/login", json={"email": "login@t.vn", "password": "123456"}).status_code == 403
    assert client.post(f"{API}/admin/users/{uid}/status", json={"status": "ACTIVE"}, headers=admin).status_code == 200
    login(client, "login@t.vn")


def test_st03_logout_revokes_refresh_token(client):
    """ST-03 · FR-1.2: sau khi đăng xuất, refresh token không còn làm mới được phiên."""
    session = client.post(
        f"{API}/auth/register",
        json={"email": "logout@t.vn", "password": "123456", "full_name": "Dang Xuat", "role": "CANDIDATE"},
    ).json()
    assert client.post(f"{API}/auth/logout", json={"refresh_token": session["refresh_token"]}).status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": session["refresh_token"]}).status_code == 401


def test_st04_update_profile_name_and_phone(client):
    """ST-04 · FR-1.4: người dùng cập nhật họ tên và số điện thoại của chính mình."""
    h = register(client, "profile@t.vn", "CANDIDATE")
    r = client.put(f"{API}/users/me", json={"full_name": "Nguyen Van B", "phone": "0901234567"}, headers=h)
    assert r.status_code == 200
    me = client.get(f"{API}/users/me", headers=h).json()["user"]
    assert (me["full_name"], me["phone"]) == ("Nguyen Van B", "0901234567")


def test_st05_admin_cannot_lock_self_and_endpoints_require_admin(client):
    """ST-05 · FR-1.5, FR-8.2: quản trị viên không tự khóa mình; ứng viên/HR không gọi được API quản trị."""
    admin = login(client, "admin@t.vn")
    admin_id = client.get(f"{API}/users/me", headers=admin).json()["user"]["id"]
    assert client.post(f"{API}/admin/users/{admin_id}/status", json={"status": "LOCKED"}, headers=admin).status_code == 400
    cand = register(client, "rbac-uv@t.vn", "CANDIDATE")
    hr = register(client, "rbac-hr@t.vn", "HR", "RBAC Co")
    for path in ("/admin/users", "/admin/stats", "/admin/orders", "/admin/transactions", "/admin/audit-logs"):
        assert client.get(f"{API}{path}", headers=cand).status_code == 403
        assert client.get(f"{API}{path}", headers=hr).status_code == 403
        assert client.get(f"{API}{path}").status_code == 401
    users = client.get(f"{API}/admin/users", params={"role": "HR"}, headers=admin).json()
    assert {u["email"] for u in users["items"]} == {"rbac-hr@t.vn"}


# ---------------------------------------------------------------- FR-2: CV và hồ sơ công ty


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_st06_upload_docx_cv_extracts_skills_and_protects_file(client):
    """ST-06 · FR-2.1, FR-2.2, NFR-04: tải CV DOCX, trích kỹ năng; chỉ chủ CV/quản trị viên tải được file gốc."""
    owner = register(client, "docx@t.vn", "CANDIDATE")
    docx = ("cv.docx", _docx_bytes(CV_TEXT), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    r = client.post(f"{API}/cvs", files={"file": docx}, headers=owner)
    assert r.status_code == 200, r.text
    cv = r.json()
    assert {"Java", "Spring Boot", "PostgreSQL"} <= set(cv["skills"])
    assert client.get(f"{API}/cvs/{cv['id']}/file", headers=owner).status_code == 200
    other = register(client, "docx-other@t.vn", "CANDIDATE")
    assert client.get(f"{API}/cvs/{cv['id']}/file", headers=other).status_code == 403
    assert client.get(f"{API}/cvs/{cv['id']}", headers=other).status_code == 404
    assert client.get(f"{API}/cvs/{cv['id']}/file", headers=login(client, "admin@t.vn")).status_code == 200


def test_st07_cv_upload_rejects_bad_files(client):
    """ST-07 · FR-2.1: sai định dạng, file hỏng, nội dung quá ngắn hoặc không gửi gì đều bị từ chối."""
    h = register(client, "badcv@t.vn", "CANDIDATE")
    assert client.post(f"{API}/cvs", files={"file": ("cv.png", b"\x89PNG....", "image/png")}, headers=h).status_code == 400
    assert client.post(f"{API}/cvs", files={"file": ("cv.docx", b"khong phai docx", "application/zip")}, headers=h).status_code == 400
    assert client.post(f"{API}/cvs", data={"text": "Quá ngắn"}, headers=h).status_code == 400
    assert client.post(f"{API}/cvs", headers=h).status_code == 400
    assert client.get(f"{API}/cvs", headers=h).json() == []


def test_st08_manage_multiple_cvs_and_delete_rules(world):
    """ST-08 · FR-2.1: ứng viên có nhiều CV; xóa được CV chưa dùng, không xóa được CV đã nộp ứng tuyển."""
    c, h = world["c"], world["cands"][0]
    second = c.post(f"{API}/cvs", data={"text": CV_TEXT + "\nReact, TypeScript", "title": "CV 2"}, headers=h).json()
    assert len(c.get(f"{API}/cvs", headers=h).json()) == 2
    apply(world)
    used = next(cv for cv in c.get(f"{API}/cvs", headers=h).json() if cv["id"] != second["id"])
    assert c.delete(f"{API}/cvs/{used['id']}", headers=h).status_code == 409
    assert c.delete(f"{API}/cvs/{second['id']}", headers=h).status_code == 200
    assert [cv["id"] for cv in c.get(f"{API}/cvs", headers=h).json()] == [used["id"]]


def test_st09_company_profile_lifecycle_and_moderation(client):
    """ST-09 · FR-2.5, FR-8.1: HR cập nhật hồ sơ công ty; bị từ chối thì sửa lại chuyển về chờ duyệt; có thông báo."""
    admin = login(client, "admin@t.vn")
    hr = register(client, "company@t.vn", "HR", "Công ty A")
    company = client.get(f"{API}/companies/me", headers=hr).json()
    assert company["status"] == "PENDING"
    assert client.post(f"{API}/companies", json={"name": "Công ty B"}, headers=hr).status_code == 409
    rejected = client.post(
        f"{API}/admin/companies/{company['id']}/review", json={"status": "REJECTED", "note": "Thiếu mô tả"}, headers=admin
    )
    assert rejected.json()["status"] == "REJECTED"
    notes = client.get(f"{API}/notifications", headers=hr).json()["items"]
    assert any("bị từ chối" in n["title"] and "Thiếu mô tả" in n["title"] for n in notes)
    assert client.get(f"{API}/companies/{company['id']}").status_code == 404
    updated = client.put(
        f"{API}/companies/me",
        json={"name": "Công ty A", "description": "Phần mềm", "location": "Hà Nội", "website": "https://a.vn"},
        headers=hr,
    ).json()
    assert updated["status"] == "PENDING" and updated["location"] == "Hà Nội"
    assert client.post(f"{API}/admin/companies/{company['id']}/review", json={"status": "BOGUS"}, headers=admin).status_code == 400
    client.post(f"{API}/admin/companies/{company['id']}/review", json={"status": "APPROVED"}, headers=admin)
    assert client.get(f"{API}/companies/{company['id']}").json()["name"] == "Công ty A"


# ---------------------------------------------------------------- FR-3: tin tuyển dụng


def test_st10_unapproved_company_cannot_post_and_job_input_is_validated(client):
    """ST-10 · FR-3.1: công ty chưa duyệt không đăng tin; tin thiếu dữ liệu hoặc lương sai khoảng bị từ chối."""
    admin = login(client, "admin@t.vn")
    hr = register(client, "post@t.vn", "HR", "Post Co")
    job = {"title": "Python Developer", "description": "Phát triển API bằng Python, FastAPI và PostgreSQL cho hệ thống."}
    assert client.post(f"{API}/jobs", json=job, headers=hr).status_code == 409
    cid = client.get(f"{API}/companies/me", headers=hr).json()["id"]
    client.post(f"{API}/admin/companies/{cid}/review", json={"status": "APPROVED"}, headers=admin)
    assert client.post(f"{API}/jobs", json={**job, "description": "Quá ngắn"}, headers=hr).status_code == 422
    assert client.post(f"{API}/jobs", json={**job, "salary_min": 30_000_000, "salary_max": 10_000_000}, headers=hr).status_code == 422
    assert client.post(f"{API}/jobs", json={**job, "salary_min": -1}, headers=hr).status_code == 422
    assert client.post(f"{API}/jobs", json={**job, "salary_min": 10_000_000, "salary_max": 20_000_000}, headers=hr).status_code == 200


def test_st11_admin_moderates_job_with_reason(world):
    """ST-11 · FR-8.1, FR-3.1: tin bị từ chối không công khai; chỉ duyệt được tin đang chờ duyệt."""
    c, hr, admin = world["c"], world["hr"], world["admin"]
    job = c.post(
        f"{API}/jobs",
        json={"title": "Tester", "description": "Kiểm thử phần mềm, viết test case, Selenium và Postman cho dự án."},
        headers=hr,
    ).json()
    assert job["status"] == "PENDING"
    r = c.patch(f"{API}/admin/jobs/{job['id']}/moderate", json={"status": "REJECTED", "note": "Mô tả chưa rõ"}, headers=admin)
    assert r.status_code == 200
    assert c.get(f"{API}/jobs/{job['id']}").status_code == 404
    assert c.patch(f"{API}/admin/jobs/{job['id']}/moderate", json={"status": "PUBLISHED"}, headers=admin).status_code == 409
    assert job["id"] not in {j["id"] for j in c.get(f"{API}/jobs").json()["items"]}


def test_st12_hr_dashboard_stats_count_own_company_only(world):
    """ST-12 · FR-3.5: thống kê HR đếm đúng tin và đơn của công ty mình."""
    c = world["c"]
    apply(world, 0)
    stats = c.get(f"{API}/jobs/stats", headers=world["hr"]).json()
    assert stats["applications_by_status"] == {"NEW": 1}
    assert stats["jobs_by_status"] == {"PUBLISHED": 1}
    other = register(c, "hr2@t.vn", "HR", "Công ty khác")
    assert c.get(f"{API}/jobs/stats", headers=other).json()["applications_by_status"] == {}


# ---------------------------------------------------------------- FR-5: ứng tuyển


def test_st13_candidate_tracks_own_applications_only(world):
    """ST-13 · FR-5.2: ứng viên chỉ thấy đơn của mình và trạng thái mới nhất."""
    c = world["c"]
    a = apply(world, 0)
    hr_move(world, a["id"], "SCREENING")
    mine = c.get(f"{API}/applications", headers=world["cands"][0]).json()
    assert [(x["id"], x["status"]) for x in mine] == [(a["id"], "SCREENING")]
    assert c.get(f"{API}/applications", headers=world["cands"][1]).json() == []


def test_st14_hr_lists_applications_only_for_owned_jobs(world):
    """ST-14 · FR-5.3, FR-1.5: HR xem/lọc danh sách đơn của tin mình; HR khác không xem được."""
    c, job = world["c"], world["job"]
    a0, a1 = apply(world, 0), apply(world, 1)
    hr_move(world, a1["id"], "SCREENING")
    listing = c.get(f"{API}/applications/jobs/{job['id']}", headers=world["hr"]).json()
    assert {x["id"] for x in listing["items"]} == {a0["id"], a1["id"]}
    screening = c.get(f"{API}/applications/jobs/{job['id']}", params={"status": "SCREENING"}, headers=world["hr"]).json()
    assert [x["id"] for x in screening["items"]] == [a1["id"]]
    other = register(c, "hr-other@t.vn", "HR", "Other")
    assert c.get(f"{API}/applications/jobs/{job['id']}", headers=other).status_code == 404
    assert hr_move({**world, "hr": other}, a0["id"], "SCREENING").status_code == 404


def test_st15_hr_rejects_and_candidate_cannot_withdraw_final_application(world):
    """ST-15 · FR-5.4: HR từ chối đơn; đơn đã kết thúc không rút được; ứng viên khác không rút hộ."""
    c = world["c"]
    a = apply(world, 0)
    assert c.post(f"{API}/applications/{a['id']}/withdraw", headers=world["cands"][1]).status_code == 404
    assert hr_move(world, a["id"], "REJECTED").status_code == 200
    assert c.post(f"{API}/applications/{a['id']}/withdraw", headers=world["cands"][0]).status_code == 409
    notes = c.get(f"{API}/notifications", headers=world["cands"][0]).json()
    assert notes["unread"] >= 1


def test_st16_cannot_apply_to_unpublished_job_or_without_cv(world):
    """ST-16 · FR-5.1: không ứng tuyển tin chưa mở; ứng viên chưa có CV bị yêu cầu tải CV."""
    c = world["c"]
    draft = c.post(
        f"{API}/jobs",
        json={"title": "Draft job", "description": "Mô tả đủ dài cho một tin nháp chưa được gửi duyệt.", "submit": False},
        headers=world["hr"],
    ).json()
    assert c.post(f"{API}/applications", json={"job_id": draft["id"]}, headers=world["cands"][0]).status_code == 404
    no_cv = register(c, "nocv@t.vn", "CANDIDATE")
    assert c.post(f"{API}/applications", json={"job_id": world["job"]["id"]}, headers=no_cv).status_code == 400


# ---------------------------------------------------------------- FR-6: phỏng vấn


def _slot_payload(start, hours=1):
    return {"start_at": start.isoformat(), "end_at": (start + timedelta(hours=hours)).isoformat(), "minutes": 30}


def test_st17_slots_must_be_in_future_and_valid(world):
    """ST-17 · FR-6.1: không tạo khung giờ trong quá khứ, khoảng thời gian ngược hoặc trên tin của HR khác."""
    c, job = world["c"], world["job"]
    url = f"{API}/jobs/{job['id']}/interview-slots"
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0)
    assert c.post(url, json=_slot_payload(past), headers=world["hr"]).status_code == 400
    future = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    reversed_range = {"start_at": future.isoformat(), "end_at": (future - timedelta(hours=1)).isoformat(), "minutes": 30}
    assert c.post(url, json=reversed_range, headers=world["hr"]).status_code == 400
    other = register(c, "slot-hr@t.vn", "HR", "Slot Co")
    assert c.post(url, json=_slot_payload(future), headers=other).status_code == 404
    created = c.post(url, json=_slot_payload(future), headers=world["hr"])
    assert created.status_code == 200 and len(created.json()) == 2


def test_st18_candidate_sees_slots_only_for_own_invited_application(world):
    """ST-18 · FR-6.2: ứng viên xem khung trống của đơn mình; đơn chưa được mời không giữ chỗ được."""
    c, job = world["c"], world["job"]
    a = apply(world, 0)
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    slots = c.post(f"{API}/jobs/{job['id']}/interview-slots", json=_slot_payload(start), headers=world["hr"]).json()
    hold = {"application_id": a["id"]}
    assert c.post(f"{API}/interview-slots/{slots[0]['id']}/hold", json=hold, headers=world["cands"][0]).status_code == 409
    hr_move(world, a["id"], "SCREENING")
    hr_move(world, a["id"], "INTERVIEW_INVITED")
    visible = c.get(f"{API}/applications/{a['id']}/slots", headers=world["cands"][0]).json()
    assert {s["id"] for s in visible} == {s["id"] for s in slots}
    assert c.get(f"{API}/applications/{a['id']}/slots", headers=world["cands"][1]).status_code == 404


# ---------------------------------------------------------------- FR-7: thanh toán


def test_st19_owner_cancels_pending_order_only(world):
    """ST-19 · FR-7.5: chủ đơn hủy đơn đang chờ; không hủy lại, không hủy đơn của người khác."""
    c, h = world["c"], world["cands"][0]
    o = _order(c, h, "CAND")
    assert c.post(f"{API}/orders/{o['id']}/cancel", headers=world["cands"][1]).status_code == 404
    assert c.post(f"{API}/orders/{o['id']}/cancel", headers=h).json()["status"] == "CANCELLED"
    assert c.post(f"{API}/orders/{o['id']}/cancel", headers=h).status_code == 409
    assert c.get(f"{API}/orders/{o['id']}", headers=h).json()["qr_url"] is None
    assert _order(c, h, "CAND")["id"] != o["id"]


def test_st20_order_rules_for_role_and_inactive_package(world):
    """ST-20 · FR-7.1, FR-7.2: không mua gói khác vai trò hoặc gói đã ngừng bán; đơn chờ được dùng lại, không tạo trùng."""
    c, h, admin = world["c"], world["cands"][0], world["admin"]
    pkgs = {p["code"]: p for p in c.get(f"{API}/admin/packages", headers=admin).json()}
    assert c.post(f"{API}/orders", json={"package_id": pkgs["HR_BASIC"]["id"]}, headers=h).status_code == 403
    first, again = _order(c, h, "CAND"), _order(c, h, "CAND")
    assert first["id"] == again["id"] and first["order_code"].startswith(settings.order_prefix)
    cand = pkgs["CAND"]
    payload = {k: cand[k] for k in ("code", "name", "target", "price", "duration_days", "quota_jobs")}
    assert c.post(f"{API}/admin/packages", json={**payload, "active": False}, headers=admin).status_code == 200
    assert cand["id"] not in {p["id"] for p in c.get(f"{API}/packages", headers=h).json()}
    other = world["cands"][1]
    assert c.post(f"{API}/orders", json={"package_id": cand["id"]}, headers=other).status_code == 400


def test_st21_refund_window_and_admin_decisions(world, monkeypatch):
    """ST-21 · FR-7.6, FR-8.3: hoàn tiền quá hạn bị chặn; duyệt hoàn tiền thu hồi Premium; từ chối giữ đơn PAID."""
    monkeypatch.setattr(settings, "payment_demo_enabled", True)
    c, admin = world["c"], world["admin"]
    late, h_late = _order(c, world["cands"][0], "CAND"), world["cands"][0]
    c.post(f"{API}/orders/{late['id']}/demo-payment", headers=h_late)
    with SessionLocal() as db:
        db.get(Order, late["id"]).paid_at = now() - timedelta(days=settings.refund_window_days + 1)
        db.commit()
    assert c.post(f"{API}/orders/{late['id']}/refund", json={"reason": "Không dùng"}, headers=h_late).status_code == 409

    h = world["cands"][1]
    o = _order(c, h, "CAND")
    assert c.post(f"{API}/orders/{o['id']}/refund", json={"reason": "Chưa trả"}, headers=h).status_code == 409
    c.post(f"{API}/orders/{o['id']}/demo-payment", headers=h)
    assert c.get(f"{API}/users/me", headers=h).json()["user"]["is_premium"] is True
    asked = c.post(f"{API}/orders/{o['id']}/refund", json={"reason": "Mua nhầm"}, headers=h).json()
    assert asked["status"] == "REFUND_REQUESTED"
    refund_id = asked["refund"]["id"]
    assert c.post(f"{API}/admin/refunds/{refund_id}", json={"approve": True, "note": "OK"}, headers=admin).status_code == 200
    assert c.get(f"{API}/orders/{o['id']}", headers=h).json()["status"] == "REFUNDED"
    assert c.get(f"{API}/users/me", headers=h).json()["user"]["is_premium"] is False
    assert c.post(f"{API}/admin/refunds/{refund_id}", json={"approve": False}, headers=admin).status_code == 409


def test_st22_admin_monitors_orders_transactions_and_stats(world, monkeypatch):
    """ST-22 · FR-8.3, FR-8.4: quản trị viên thấy đơn, giao dịch và chỉ số doanh thu sau thanh toán."""
    monkeypatch.setattr(settings, "payment_demo_enabled", True)
    c, admin, h = world["c"], world["admin"], world["cands"][0]
    o = _order(c, h, "CAND")
    c.post(f"{API}/orders/{o['id']}/demo-payment", headers=h)
    orders = c.get(f"{API}/admin/orders", params={"q": o["order_code"]}, headers=admin).json()
    assert [x["status"] for x in orders["items"]] == ["PAID"]
    stats = c.get(f"{API}/admin/stats", headers=admin).json()
    assert stats["revenue"] == o["amount"]
    assert stats["users"]["CANDIDATE"] == 2 and stats["jobs"]["PUBLISHED"] == 1
    assert stats["orders"] == {"PAID": 1}
    report = c.get(f"{API}/admin/reconcile", headers=admin).json()
    assert report["total_received"] == o["amount"] and report["problems"] == []


# ---------------------------------------------------------------- Thông báo, sức khỏe hệ thống


def test_st23_notifications_list_and_mark_all_read(world):
    """ST-23 · Thông báo: sự kiện nghiệp vụ tạo thông báo; đánh dấu đã đọc đưa số chưa đọc về 0."""
    c = world["c"]
    a = apply(world, 0)
    hr_move(world, a["id"], "SCREENING")
    h = world["cands"][0]
    before = c.get(f"{API}/notifications", headers=h).json()
    assert before["unread"] >= 1 and before["items"]
    assert c.post(f"{API}/notifications/read-all", headers=h).status_code == 200
    after = c.get(f"{API}/notifications", headers=h).json()
    assert after["unread"] == 0 and all(n["read"] for n in after["items"])


def test_st24_health_endpoint(client):
    """ST-24 · NFR-05: endpoint kiểm tra sức khỏe phục vụ giám sát triển khai."""
    r = client.get(f"{API}/health")
    assert r.status_code == 200
