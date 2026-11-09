"""Kiểm thử giao diện end-to-end (Playwright): đi hết các luồng chính bằng 3 vai trò.

Yêu cầu: backend chạy ở :8000, frontend ở :5173, DB đã seed.
  python e2e/smoke_ui.py          -> ảnh chụp trong e2e/screenshots/
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:5173"
SHOTS = ROOT / "e2e/screenshots"
problems = []


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.wait_for_timeout(600)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    print("  ảnh:", name)


def watch(page, who):
    page.on("console", lambda m: m.type == "error" and problems.append(f"[{who}] console: {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"[{who}] pageerror: {e}"))
    page.on("response", lambda r: r.status >= 500 and problems.append(f"[{who}] HTTP {r.status} {r.url}"))


def login(page, email):
    page.goto(f"{BASE}/login")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", "123456")
    page.click("form button:has-text('Đăng nhập')")
    page.wait_for_load_state("networkidle")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        def new_ctx():   # mỗi vai trò 1 context riêng (localStorage/token tách biệt)
            return browser.new_context(viewport={"width": 1366, "height": 860}, locale="vi-VN")
        ctx = new_ctx()

        # ---------------- Khách
        page = ctx.new_page()
        watch(page, "guest")
        print("Khách: trang chủ, tìm việc, chi tiết tin")
        page.goto(BASE)
        expect(page.get_by_text("Việc làm nổi bật")).to_be_visible()
        shot(page, "01_home")
        page.goto(f"{BASE}/jobs?q=java")
        page.wait_for_selector("text=Tìm thấy")
        shot(page, "02_jobs_search")
        page.goto(f"{BASE}/companies")
        page.wait_for_load_state("networkidle")

        # ---------------- Ứng viên: gợi ý AI, upload CV, ứng tuyển tin của hr@demo.vn
        print("Ứng viên: gợi ý AI, tải CV, ứng tuyển")
        cand = new_ctx().new_page()
        watch(cand, "candidate")
        login(cand, "candidate@demo.vn")
        cand.goto(f"{BASE}/candidate/recommendations")
        cand.wait_for_selector("text=phù hợp", timeout=30000)
        cand.locator("text=Vì sao phù hợp?").first.click()
        shot(cand, "03_candidate_recommendations")

        cand.goto(f"{BASE}/candidate/cvs")
        pdf = next((ROOT / "data/cv_files").glob("*.pdf"))
        cand.set_input_files("input[type=file]", str(pdf))
        cand.click("text=Tải lên & phân tích")
        cand.wait_for_selector("text=Kết quả trích xuất CV", timeout=60000)
        shot(cand, "04_candidate_cv_parsed")
        cand.keyboard.press("Escape")

        # tìm 1 tin của hr@demo.vn mà ứng viên chưa nộp
        cand.goto(f"{BASE}/jobs")
        hr_page = new_ctx().new_page()
        watch(hr_page, "hr")
        login(hr_page, "hr@demo.vn")
        jobs = hr_page.evaluate("fetch('/api/v1/jobs/owned',{headers:{Authorization:'Bearer '+localStorage.token}}).then(r=>r.json())")
        api = "fetch('{}',{{headers:{{Authorization:'Bearer '+localStorage.token}}}}).then(r=>r.json())"
        applied = {a["job"]["id"] for a in cand.evaluate(api.format("/api/v1/applications"))}
        me = cand.evaluate(api.format("/api/v1/users/me"))["user"]["full_name"]
        target = [j for j in jobs if j["status"] == "PUBLISHED" and j["id"] not in applied][-1]
        cand.goto(f"{BASE}/jobs/{target['id']}")
        cand.wait_for_selector("text=Mức độ phù hợp với bạn")
        cand.wait_for_selector("text=Kỹ năng còn thiếu", timeout=30000)
        shot(cand, "05_candidate_job_match")
        if cand.locator("button:has-text('Ứng tuyển ngay')").count():
            cand.click("button:has-text('Ứng tuyển ngay')")
            cand.click("button:has-text('Gửi hồ sơ')")
            cand.wait_for_selector("text=Ứng tuyển thành công")

        # ---------------- HR: dashboard, hồ sơ, mời phỏng vấn, AI gợi ý, lịch
        print("HR: tổng quan, xử lý hồ sơ, mời phỏng vấn, AI gợi ý, lịch")
        hr_page.goto(f"{BASE}/hr")
        hr_page.wait_for_selector("text=Tin đang hiển thị")
        shot(hr_page, "06_hr_dashboard")
        hr_page.goto(f"{BASE}/hr/jobs/{target['id']}")
        hr_page.wait_for_selector("text=Hồ sơ ứng tuyển")
        row = hr_page.locator("tr", has_text=me).first
        row.locator("text=Xem & xử lý").click()
        hr_page.wait_for_selector("text=Xử lý hồ sơ")
        shot(hr_page, "07_hr_application_detail")
        for label in ("Chuyển sàng lọc", "Mời phỏng vấn"):
            hr_page.locator(".fixed button", has_text=label).first.click()
            hr_page.wait_for_timeout(700)
        hr_page.keyboard.press("Escape")
        hr_page.click("button:has-text('Ứng viên AI gợi ý')")
        hr_page.wait_for_selector("text=Danh sách xếp hạng", timeout=30000)
        hr_page.locator("button:has-text('Phân tích')").first.click()
        invite = hr_page.locator("button:has-text('Mời ứng tuyển')")
        if invite.count():
            invite.first.click()
            hr_page.wait_for_selector("text=Đã mời")
        shot(hr_page, "08_hr_ai_candidates")
        hr_page.click("button:has-text('Lịch phỏng vấn')")
        hr_page.wait_for_selector("text=Mở khung giờ phỏng vấn")
        import datetime as _dt
        day = (_dt.date.today() + _dt.timedelta(days=5)).isoformat()
        inputs = hr_page.locator("input[type=datetime-local]")
        inputs.nth(0).fill(f"{day}T14:00")
        inputs.nth(1).fill(f"{day}T16:00")
        hr_page.click("button:has-text('Tạo khung giờ')")
        hr_page.wait_for_selector("td:has-text('Trống')")
        hr_page.wait_for_timeout(1000)
        shot(hr_page, "09_hr_slots")

        # ---------------- Ứng viên chọn lịch: giữ chỗ -> xác nhận
        print("Ứng viên: giữ chỗ và xác nhận lịch phỏng vấn")
        cand.goto(f"{BASE}/candidate/applications")
        cand.locator("button:has-text('Chọn lịch phỏng vấn')").first.click()
        cand.wait_for_selector("text=Chọn 1 khung giờ")
        cand.locator(".fixed button.rounded-lg.border").first.click()
        cand.wait_for_selector("text=Đang giữ chỗ")
        shot(cand, "10_candidate_slot_held")
        cand.click("button:has-text('Xác nhận lịch')")
        cand.wait_for_selector("text=Lịch phỏng vấn:")
        shot(cand, "11_candidate_applications")

        # ---------------- Thanh toán Premium demo
        print("Ứng viên: mua Premium bằng thanh toán demo")
        cand.goto(f"{BASE}/premium")
        cand.get_by_role("button", name="Mua gói", exact=False).first.click()
        expect(cand.get_by_role("button", name="Thanh toán demo", exact=True)).to_be_visible()
        expect(cand.locator('img[alt="VietQR"]')).to_have_count(0)
        shot(cand, "12_checkout_demo")
        cand.get_by_role("button", name="Thanh toán demo", exact=True).click()
        cand.wait_for_selector("text=Thanh toán thành công", timeout=15000)
        shot(cand, "13_checkout_paid")
        assert cand.evaluate(api.format("/api/v1/users/me"))["user"]["is_premium"], "Premium chưa được kích hoạt"
        cand.goto(f"{BASE}/candidate/recommendations")
        cand.wait_for_selector("text=phù hợp", timeout=30000)
        assert cand.locator("text=Nâng cấp Premium").count() == 0, "Premium chưa được kích hoạt"

        # ---------------- Admin
        print("Admin: thống kê, kiểm duyệt, đối soát")
        adm = new_ctx().new_page()
        watch(adm, "admin")
        login(adm, "admin@demo.vn")
        adm.goto(f"{BASE}/admin")
        adm.wait_for_selector("text=Doanh thu 30 ngày")
        shot(adm, "14_admin_dashboard")
        adm.goto(f"{BASE}/admin/payments")
        adm.click("button:has-text('Đối soát')")
        adm.wait_for_selector("text=Tổng tiền nhận")
        shot(adm, "15_admin_reconcile")
        adm.goto(f"{BASE}/admin/moderation")
        adm.wait_for_load_state("networkidle")
        adm.goto(f"{BASE}/admin/audit")
        adm.wait_for_selector("text=Nhật ký thao tác")
        shot(adm, "16_admin_audit")
        browser.close()

    print("\nVấn đề phát hiện:" if problems else "\nKhông có lỗi console/HTTP 5xx.")
    for pr in problems:
        print(" -", pr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
