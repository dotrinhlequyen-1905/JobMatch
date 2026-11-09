"""Kiểm thử các luồng nghiệp vụ khó: máy trạng thái, đặt lịch đồng thời, webhook idempotent, hoàn tiền, RBAC."""

import threading
from datetime import datetime, timedelta, timezone
from app.core.database import SessionLocal
from app.models import InterviewSlot, Order
from tests.conftest import register


def apply(w, i=0):
    r = w["c"].post("/api/v1/applications", json={"job_id": w["job"]["id"]}, headers=w["cands"][i])
    assert r.status_code == 200, r.text
    return r.json()


def hr_move(w, app_id, to):
    return w["c"].patch(f"/api/v1/applications/{app_id}/status", json={"to": to}, headers=w["hr"])


def test_cv_parsed_and_match(world):
    c, h = (world["c"], world["cands"][0])
    cv = c.get("/api/v1/cvs", headers=h).json()[0]
    assert {"Java", "Spring Boot", "PostgreSQL", "Docker"} <= set(cv["skills"])
    assert cv["years"] >= 4
    m = c.get(f"/api/v1/matching/jobs/{world['job']['id']}/match", headers=h).json()["match"]
    assert "Kafka" in m["missing_skills"] and "Java" in m["matched_skills"]
    rec = c.get("/api/v1/matching/jobs", headers=h).json()
    assert rec["items"][0]["job"]["id"] == world["job"]["id"]
    ranked = c.get(f"/api/v1/jobs/{world['job']['id']}/candidates", headers=world["hr"]).json()
    assert len(ranked) == 2


def test_application_state_machine(world):
    app = apply(world)
    assert app["status"] == "NEW"
    assert (
        world["c"]
        .post("/api/v1/applications", json={"job_id": world["job"]["id"]}, headers=world["cands"][0])
        .status_code
        == 409
    )
    assert hr_move(world, app["id"], "INTERVIEWED").status_code == 409
    assert hr_move(world, app["id"], "WITHDRAWN").status_code == 403
    assert hr_move(world, app["id"], "SCREENING").status_code == 200
    assert hr_move(world, app["id"], "INTERVIEW_INVITED").status_code == 200
    r = world["c"].post(f"/api/v1/applications/{app['id']}/withdraw", headers=world["cands"][0])
    assert r.json()["status"] == "WITHDRAWN"
    assert hr_move(world, app["id"], "SCREENING").status_code == 409
    hist = [h["to"] for h in r.json()["history"]]
    assert hist == ["NEW", "SCREENING", "INTERVIEW_INVITED", "WITHDRAWN"]


def _invited_apps(world):
    ids = []
    for i in range(2):
        a = apply(world, i)
        hr_move(world, a["id"], "SCREENING")
        hr_move(world, a["id"], "INTERVIEW_INVITED")
        ids.append(a["id"])
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    slots = (
        world["c"]
        .post(
            f"/api/v1/jobs/{world['job']['id']}/interview-slots",
            headers=world["hr"],
            json={"start_at": start.isoformat(), "end_at": (start + timedelta(hours=1)).isoformat(), "minutes": 30},
        )
        .json()
    )
    return (ids, slots)


def test_slot_overlap_rejected(world):
    _, slots = _invited_apps(world)
    r = world["c"].post(
        f"/api/v1/jobs/{world['job']['id']}/interview-slots",
        headers=world["hr"],
        json={"start_at": slots[0]["start_at"], "end_at": slots[-1]["end_at"], "minutes": 30},
    )
    assert r.status_code == 409


def test_candidate_cannot_book_overlapping_interviews(world):
    """Ứng viên ứng tuyển 2 công ty: không giữ được 2 khung giờ chồng nhau, khác giờ thì được."""
    c, h0 = (world["c"], world["cands"][0])
    apps, slots = _invited_apps(world)
    assert c.post(f"/api/v1/interview-slots/{slots[0]['id']}/hold", json={"application_id": apps[0]}, headers=h0).status_code == 200
    assert c.post(f"/api/v1/interview-slots/{slots[0]['id']}/book", headers=h0).status_code == 200

    hr2 = register(c, "hr-other@t.vn", "HR", "Công ty U")
    cid = c.get("/api/v1/companies/me", headers=hr2).json()["id"]
    c.post(f"/api/v1/admin/companies/{cid}/review", json={"status": "APPROVED"}, headers=world["admin"])
    desc = "Yêu cầu 2 năm kinh nghiệm Java, Spring Boot, PostgreSQL, Docker. Làm việc tại Hà Nội."
    job2 = c.post("/api/v1/jobs", headers=hr2, json={"title": "Java Developer", "description": desc}).json()
    c.patch(f"/api/v1/admin/jobs/{job2['id']}/moderate", json={"status": "PUBLISHED"}, headers=world["admin"])
    app2 = c.post("/api/v1/applications", json={"job_id": job2["id"]}, headers=h0).json()["id"]
    for to in ("SCREENING", "INTERVIEW_INVITED"):
        c.patch(f"/api/v1/applications/{app2}/status", json={"to": to}, headers=hr2)
    # Công ty U mở lịch 15 phút sau lịch đã đặt ở công ty T: khung đầu chồng giờ, khung sau thì không.
    start = datetime.fromisoformat(slots[0]["start_at"]) + timedelta(minutes=15)
    other = c.post(
        f"/api/v1/jobs/{job2['id']}/interview-slots",
        headers=hr2,
        json={"start_at": start.isoformat(), "end_at": (start + timedelta(minutes=60)).isoformat(), "minutes": 30},
    ).json()
    r = c.post(f"/api/v1/interview-slots/{other[0]['id']}/hold", json={"application_id": app2}, headers=h0)
    assert r.status_code == 409 and "trùng" in r.json()["detail"]
    assert c.post(f"/api/v1/interview-slots/{other[1]['id']}/hold", json={"application_id": app2}, headers=h0).status_code == 200


def test_concurrent_hold_only_one_wins(world):
    """2 ứng viên bấm giữ cùng 1 slot đồng thời (lặp 10 lần) -> mỗi lần đúng 1 người thành công."""
    apps, slots = _invited_apps(world)
    c = world["c"]
    for _ in range(10):
        results = []
        barrier = threading.Barrier(2)

        def go(i):
            barrier.wait()
            r = c.post(
                f"/api/v1/interview-slots/{slots[0]['id']}/hold",
                json={"application_id": apps[i]},
                headers=world["cands"][i],
            )
            results.append(r.status_code)

        ts = [threading.Thread(target=go, args=(i,)) for i in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert sorted(results) == [200, 409], results
        with SessionLocal() as db:
            s = db.get(InterviewSlot, slots[0]["id"])
            s.status, s.held_by, s.held_until, s.application_id = ("OPEN", None, None, None)
            db.commit()


def test_hold_confirm_and_expiry(world):
    apps, slots = _invited_apps(world)
    c, h0, h1 = (world["c"], world["cands"][0], world["cands"][1])
    assert (
        c.post(
            f"/api/v1/interview-slots/{slots[0]['id']}/hold", json={"application_id": apps[0]}, headers=h0
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/v1/interview-slots/{slots[0]['id']}/hold", json={"application_id": apps[1]}, headers=h1
        ).status_code
        == 409
    )
    assert c.post(f"/api/v1/interview-slots/{slots[0]['id']}/book", headers=h1).status_code == 409
    with SessionLocal() as db:
        db.get(InterviewSlot, slots[0]["id"]).held_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert c.post(f"/api/v1/interview-slots/{slots[0]['id']}/book", headers=h0).status_code == 409
    assert (
        c.post(
            f"/api/v1/interview-slots/{slots[0]['id']}/hold", json={"application_id": apps[1]}, headers=h1
        ).status_code
        == 200
    )
    r = c.post(f"/api/v1/interview-slots/{slots[0]['id']}/book", headers=h1)
    assert r.status_code == 200 and r.json()["status"] == "BOOKED"
    app = [a for a in c.get("/api/v1/applications", headers=h1).json() if a["id"] == apps[1]][0]
    assert app["status"] == "INTERVIEW_SCHEDULED"
    assert (
        c.post(
            f"/api/v1/interview-slots/{slots[0]['id']}/result", json={"result": "PASS"}, headers=world["hr"]
        ).status_code
        == 200
    )
    assert hr_move(world, apps[1], "OFFERED").status_code == 200


def _order(c, h, code):
    pkgs = {p["code"]: p for p in c.get("/api/v1/packages", headers=h).json()}
    r = c.post("/api/v1/orders", json={"package_id": pkgs[code]["id"]}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _webhook(c, tx_id, content, amount, key="dev-sepay-key"):
    return c.post(
        "/api/v1/webhooks/sepay",
        headers={"Authorization": f"Apikey {key}"},
        json={"id": tx_id, "content": content, "transferType": "in", "transferAmount": amount},
    )


def test_webhook_idempotent_and_activation(world):
    c, h = (world["c"], world["cands"][0])
    o = _order(c, h, "CAND")
    assert "qr.sepay.vn" in o["qr_url"]
    assert _webhook(c, "TX1", f"thanh toan {o['order_code']}", o["amount"], key="sai").status_code == 401
    assert _webhook(c, "TX1", f"thanh toan {o['order_code']}", o["amount"]).json()["status"] == "MATCHED"
    assert _webhook(c, "TX1", f"thanh toan {o['order_code']}", o["amount"]).json()["status"] == "DUPLICATE"
    assert _webhook(c, "TX2", f"thanh toan {o['order_code']}", o["amount"]).json()["status"] == "LATE"
    me = c.get("/api/v1/users/me", headers=h).json()["user"]
    assert me["is_premium"]
    rec = c.get("/api/v1/matching/jobs", headers=h).json()
    assert rec["premium"] is True
    report = c.get("/api/v1/admin/reconcile", headers=world["admin"]).json()
    assert any((p["type"] == "TX_LATE" for p in report["problems"]))


def test_webhook_wrong_amount_and_unknown(world):
    c, h = (world["c"], world["cands"][0])
    o = _order(c, h, "CAND")
    assert _webhook(c, "TX3", o["order_code"], o["amount"] - 1000).json()["status"] == "AMOUNT_MISMATCH"
    assert _webhook(c, "TX4", "chuyen tien khong ro noi dung", 50000).json()["status"] == "UNMATCHED"
    assert c.get(f"/api/v1/orders/{o['id']}", headers=h).json()["status"] == "RECONCILING"


def test_order_expiry(world):
    from app.services.payments import expire_orders

    c, h = (world["c"], world["cands"][0])
    o = _order(c, h, "CAND")
    with SessionLocal() as db:
        db.get(Order, o["id"]).expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
        assert expire_orders(db) == 1
    assert _webhook(c, "TX5", o["order_code"], o["amount"]).json()["status"] == "LATE"


def test_hr_quota_and_refund(world):
    c, hr, admin = (world["c"], world["hr"], world["admin"])
    body = {"title": "Frontend React", "description": "Cần React, TypeScript, HTML/CSS, 1 năm kinh nghiệm frontend."}
    assert c.post("/api/v1/jobs", json=body, headers=hr).status_code == 200
    assert c.post("/api/v1/jobs", json=body, headers=hr).status_code == 402
    o = _order(c, hr, "HR_BASIC")
    _webhook(c, "TX10", o["order_code"], o["amount"])
    r = c.post(f"/api/v1/orders/{o['id']}/refund", json={"reason": "Mua nhầm"}, headers=hr)
    assert r.status_code == 200 and r.json()["status"] == "REFUND_REQUESTED"
    rid = c.get("/api/v1/admin/refunds", headers=admin).json()[0]["id"]
    assert c.post(f"/api/v1/admin/refunds/{rid}", json={"approve": True}, headers=admin).status_code == 200
    assert c.get(f"/api/v1/orders/{o['id']}", headers=hr).json()["status"] == "REFUNDED"
    assert c.post("/api/v1/jobs", json=body, headers=hr).status_code == 402
    o2 = _order(c, hr, "HR_BASIC")
    _webhook(c, "TX11", o2["order_code"], o2["amount"])
    assert c.post("/api/v1/jobs", json=body, headers=hr).status_code == 200
    assert c.post(f"/api/v1/orders/{o2['id']}/refund", json={"reason": "x"}, headers=hr).status_code == 409


def test_rbac(world):
    c = world["c"]
    cand, hr = (world["cands"][0], world["hr"])
    assert c.get("/api/v1/admin/stats", headers=cand).status_code == 403
    assert c.get("/api/v1/admin/stats", headers=hr).status_code == 403
    assert c.get("/api/v1/jobs/owned", headers=cand).status_code == 403
    assert c.get("/api/v1/cvs", headers=hr).status_code == 403
    assert c.get("/api/v1/cvs").status_code == 401
    other_hr = register(c, "hr2@t.vn", "HR", "Công ty khác")
    assert c.get(f"/api/v1/jobs/{world['job']['id']}/manage", headers=other_hr).status_code == 404
    assert (
        c.post(
            "/api/v1/jobs", headers=other_hr, json={"title": "Tin khi chưa duyệt", "description": "x" * 40}
        ).status_code
        == 409
    )


def test_hr_invite_candidate(world):
    c, hr = (world["c"], world["hr"])
    job_id = world["job"]["id"]
    ranked = c.get(f"/api/v1/jobs/{job_id}/candidates", headers=hr).json()
    cand_id = ranked[0]["candidate"]["id"]
    assert c.post(f"/api/v1/jobs/{job_id}/invite", json={"candidate_id": cand_id}, headers=hr).status_code == 200
    assert c.post(f"/api/v1/jobs/{job_id}/invite", json={"candidate_id": cand_id}, headers=hr).status_code == 409
    again = c.get(f"/api/v1/jobs/{job_id}/candidates", headers=hr).json()
    assert next((x for x in again if x["candidate"]["id"] == cand_id))["invited"] is True
    notis = [n for h in world["cands"] for n in c.get("/api/v1/notifications", headers=h).json()["items"]]
    assert any((n["link"] == f"/jobs/{job_id}" and "mời bạn ứng tuyển" in n["title"] for n in notis))
    apply(world, 1)
    applied_id = c.get("/api/v1/users/me", headers=world["cands"][1]).json()["user"]["id"]
    assert c.post(f"/api/v1/jobs/{job_id}/invite", json={"candidate_id": applied_id}, headers=hr).status_code == 409


def test_expired_job_hidden_and_closed(world):
    from app.services.expiry import close_expired_jobs
    from app.models import Job

    c, h = (world["c"], world["cands"][0])
    job_id = world["job"]["id"]
    assert any((j["id"] == job_id for j in c.get("/api/v1/jobs").json()["items"]))
    with SessionLocal() as db:
        db.get(Job, job_id).expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    assert all((j["id"] != job_id for j in c.get("/api/v1/jobs").json()["items"]))
    assert all((r["job"]["id"] != job_id for r in c.get("/api/v1/matching/jobs", headers=h).json()["items"]))
    assert c.post("/api/v1/applications", json={"job_id": job_id}, headers=h).status_code == 409
    with SessionLocal() as db:
        assert close_expired_jobs(db) == 1
        assert db.get(Job, job_id).status == "CLOSED"


def test_match_detail_is_premium_only(world):
    c, h = (world["c"], world["cands"][0])
    m = c.get(f"/api/v1/matching/jobs/{world['job']['id']}/match", headers=h).json()
    assert m["premium"] is False and "semantic" not in m["match"] and ("missing_skills" in m["match"])
    pkgs = {p["code"]: p for p in c.get("/api/v1/packages", headers=h).json()}
    o = c.post("/api/v1/orders", json={"package_id": pkgs["CAND"]["id"]}, headers=h).json()
    c.post(
        "/api/v1/webhooks/sepay",
        headers={"Authorization": "Apikey dev-sepay-key"},
        json={"id": "TXP", "content": o["order_code"], "transferType": "in", "transferAmount": o["amount"]},
    )
    m = c.get(f"/api/v1/matching/jobs/{world['job']['id']}/match", headers=h).json()
    assert m["premium"] is True and "semantic" in m["match"]


def test_admin_package_validation(world):
    c, admin = (world["c"], world["admin"])
    bad = {"code": "x", "name": "Gói", "target": "OTHER", "price": 0, "duration_days": 0}
    assert c.post("/api/v1/admin/packages", json=bad, headers=admin).status_code == 422
    ok = {"code": "HR_TEST", "name": "Gói thử", "target": "HR", "price": 99000, "duration_days": 7, "quota_jobs": 1}
    assert c.post("/api/v1/admin/packages", json=ok, headers=admin).status_code == 200
    assert any((p["code"] == "HR_TEST" for p in c.get("/api/v1/packages?target=HR", headers=admin).json()))
    assert c.post("/api/v1/admin/packages", json={**ok, "active": False}, headers=admin).status_code == 200
    assert all((p["code"] != "HR_TEST" for p in c.get("/api/v1/packages?target=HR", headers=admin).json()))
