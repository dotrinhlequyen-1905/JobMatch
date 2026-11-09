"""Chụp các trang chính ở màn hình điện thoại (390x844) để kiểm tra bố cục, báo trang nào bị tràn ngang.

  python e2e/mobile_check.py   -> e2e/screenshots/mobile_*.png
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
SHOTS = Path(__file__).resolve().parent / "screenshots"
PAGES = {
    None: [("home", "/"), ("jobs", "/jobs?q=java"), ("job_detail", "/jobs/1")],
    "candidate@demo.vn": [("recommendations", "/candidate/recommendations"), ("applications", "/candidate/applications"),
                          ("cvs", "/candidate/cvs"), ("job_detail_cand", "/jobs/1")],
    "hr@demo.vn": [("hr_dashboard", "/hr"), ("hr_jobs", "/hr/jobs")],
    "admin@demo.vn": [("admin_dashboard", "/admin"), ("admin_payments", "/admin/payments")],
}


def main():
    SHOTS.mkdir(exist_ok=True)
    overflow = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for email, pages in PAGES.items():
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True)
            page = ctx.new_page()
            if email:
                page.goto(f"{BASE}/login")
                page.fill("input[type=email]", email)
                page.fill("input[type=password]", "123456")
                page.click("form button:has-text('Đăng nhập')")
                page.wait_for_load_state("networkidle")
            for name, url in pages:
                page.goto(BASE + url)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(800)
                w = page.evaluate("document.documentElement.scrollWidth")
                if w > 392:
                    overflow.append(f"{name}: rộng {w}px")
                page.screenshot(path=str(SHOTS / f"mobile_{name}.png"), full_page=False)
                print("ảnh:", name, "| scrollWidth", w)
            ctx.close()
        browser.close()
    print("Tràn ngang:" if overflow else "Không trang nào tràn ngang.", overflow)


if __name__ == "__main__":
    main()
