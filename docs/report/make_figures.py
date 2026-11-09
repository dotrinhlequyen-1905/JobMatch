"""Vẽ sơ đồ và biểu đồ cho báo cáo -> docs/report/figures/*.png

  python docs/report/make_figures.py
"""
import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "Arial"
plt.rcParams["font.size"] = 10

C = {"blue": "#DBE6FE", "blue_e": "#2553E6", "green": "#D1FAE5", "green_e": "#059669", "amber": "#FEF3C7",
     "amber_e": "#D97706", "rose": "#FFE4E6", "rose_e": "#E11D48", "gray": "#F1F5F9", "gray_e": "#475569",
     "violet": "#EDE9FE", "violet_e": "#7C3AED"}


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color="blue", size=9, bold=False, align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc=C[color], ec=C[color + "_e"], lw=1.3))
    ax.text(x + (w / 2 if align == "center" else 1.2), y + h / 2, text, ha=align, va="center", fontsize=size,
            fontweight="bold" if bold else "normal", wrap=True, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, text="", color="#334155", style="-|>", ls="-", rad=0.0, size=8, offset=(0, 1.2)):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12, color=color, lw=1.2,
                                 linestyle=ls, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1], text, ha="center", va="bottom", fontsize=size,
                color=color, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)
    print("ok", name)


# ---------------------------------------------------------------- 1. Kiến trúc
def architecture():
    fig, ax = canvas(12, 7.2)
    box(ax, 2, 58, 22, 10, "Trình duyệt\n(Ứng viên · HR · Admin · Khách)", "gray", bold=True)
    box(ax, 34, 58, 30, 10, "Frontend: React + TypeScript\nVite · Tailwind · React Router", "blue", bold=True)
    arrow(ax, 26.6, 63, 34, 63, "HTTP")
    # backend
    ax.add_patch(FancyBboxPatch((10, 14), 78, 36, boxstyle="round,pad=0.4,rounding_size=1.5", fc="#FAFAFA",
                                ec=C["blue_e"], lw=1.6, ls="--"))
    ax.text(12, 47.5, "Backend: FastAPI (Python) — một tiến trình", fontsize=10, fontweight="bold", color=C["blue_e"])
    arrow(ax, 49, 58, 49, 50.6, "REST/JSON + JWT")
    box(ax, 13, 34, 22, 9.5, "Routers (API)\nauth · public · candidate\nhr · payments · admin", "blue", 8.5)
    box(ax, 38, 34, 22, 9.5, "Services\nmáy trạng thái · đặt lịch\nthanh toán · thông báo", "green", 8.5)
    box(ax, 63, 34, 22, 9.5, "Module AI\ntrích xuất CV · embedding\nso khớp · gap analysis", "violet", 8.5)
    box(ax, 13, 18, 22, 9.5, "Bảo mật\nJWT · bcrypt · RBAC\n(phân quyền theo vai trò)", "gray", 8.5)
    box(ax, 38, 18, 22, 9.5, "Tác vụ định kỳ (APScheduler)\ngiải phóng slot · hết hạn đơn\nđóng tin · đối soát", "amber", 8.5)
    box(ax, 63, 18, 22, 9.5, "Chỉ mục vector trong RAM\n(numpy, cosine)\n~8.000 CV + JD", "violet", 8.5)
    arrow(ax, 35, 38.7, 38, 38.7)
    arrow(ax, 60, 38.7, 63, 38.7)
    arrow(ax, 74, 34, 74, 27.5)
    # dưới
    box(ax, 12, 1, 24, 9, "PostgreSQL 17\n14 bảng · giao dịch ACID\nvector lưu dạng bytea", "green", 8.5, True)
    box(ax, 44, 1, 20, 9, "Model đã fine-tune\nmultilingual-e5-base\n(GPU RTX 4050)", "violet", 8.5, True)
    box(ax, 72, 1, 18, 9, "Lưu file CV\n(PDF/DOCX)", "gray", 8.5, True)
    arrow(ax, 30, 14, 26, 10, "SQLAlchemy")
    arrow(ax, 70, 14, 56, 10, "sentence-transformers", offset=(2, -3))
    arrow(ax, 80, 14, 81, 10)
    # SePay
    box(ax, 95, 36, 22, 12, "SePay\n(nhận tiền ngân hàng)", "rose", bold=True)
    box(ax, 95, 58, 22, 10, "Ứng dụng ngân hàng\nquét VietQR", "rose")
    arrow(ax, 106, 58, 106, 48, "chuyển khoản")
    arrow(ax, 95, 42, 88.6, 42, "webhook", offset=(0, 1))
    arrow(ax, 64, 66, 95, 66, "ảnh QR (qr.sepay.vn)", ls="--", offset=(0, 0.6))
    save(fig, "fig_architecture")


# ---------------------------------------------------------------- 2. Use case / chức năng theo vai trò
def usecases():
    fig, ax = canvas(12, 6.2)
    cols = [
        ("Khách", "gray", ["Tìm kiếm & lọc việc làm", "Xem chi tiết tin, công ty", "Đăng ký / đăng nhập"]),
        ("Ứng viên", "blue", ["Tải CV (PDF/DOCX) → AI trích xuất", "Gợi ý việc làm AI + kỹ năng thiếu",
                              "Ứng tuyển, theo dõi, rút đơn", "Giữ chỗ & xác nhận lịch PV",
                              "Mua Premium (VietQR), hoàn tiền"]),
        ("Nhà tuyển dụng", "green", ["Hồ sơ công ty, đăng/sửa/đóng tin", "Ứng viên xếp hạng bằng AI",
                                     "Mời ứng viên nộp hồ sơ", "Xử lý hồ sơ theo quy trình",
                                     "Mở lịch PV, ghi kết quả", "Mua gói đăng tin"]),
        ("Quản trị viên", "violet", ["Duyệt công ty & tin", "Khóa / mở tài khoản", "Giao dịch, đối soát, hoàn tiền",
                                     "Quản lý gói dịch vụ", "Thống kê, nhật ký thao tác"]),
    ]
    x = 2
    for title, color, items in cols:
        box(ax, x, 51, 27, 7, title, color, 11, True)
        for i, it in enumerate(items):
            box(ax, x, 42 - i * 8.2, 27, 6, it, "gray", 8.5)
        x += 30
    save(fig, "fig_usecases")


# ---------------------------------------------------------------- 3. ERD rút gọn
def erd():
    fig, ax = canvas(12, 7.5)
    ents = {
        "users": (2, 52, "users\nid · email · role\nstatus · premium_until", "blue"),
        "companies": (2, 30, "companies\nid · owner_id → users\nname · status", "gray"),
        "jobs": (2, 6, "jobs\nid · company_id → companies\ntitle · skills · min_years\nstatus · expires_at · embedding", "gray"),
        "cvs": (42, 52, "cvs\nid · candidate_id → users\nraw_text · skills · years\nparsed · embedding", "blue"),
        "applications": (42, 28, "applications\nid · job_id · candidate_id · cv_id\nstatus · match_score\nUNIQUE(job_id, candidate_id)", "green"),
        "history": (42, 4, "application_history\napplication_id · from → to\nactor_id · note", "green"),
        "orders": (84, 52, "orders\nid · user_id → users · package_id\namount · order_code (UNIQUE)\nstatus · expires_at · paid_at", "rose"),
        "tx": (84, 30, "payment_transactions\nsepay_tx_id (UNIQUE)\norder_id → orders · amount · status", "rose"),
        "slots": (84, 4, "interview_slots\nid · job_id · hr_id · start/end\nstatus · held_by · held_until\napplication_id → applications", "amber"),
    }
    for k, (x, y, t, c) in ents.items():
        box(ax, x, y, 32, 14, t, c, 8.2)
    arrow(ax, 18, 52, 18, 44.6, "1 – 1", style="-")
    arrow(ax, 18, 30, 18, 20.6, "1 – n", style="-")
    arrow(ax, 34.6, 59, 42, 59, "1 – n", style="-", offset=(0, 0.8))
    arrow(ax, 58, 52, 58, 42.6, "1 – n", style="-")
    arrow(ax, 34.6, 13, 42, 31, "1 – n", style="-", offset=(-3, 0))
    arrow(ax, 58, 28, 58, 18.6, "1 – n", style="-")
    arrow(ax, 100, 52, 100, 44.6, "1 – n", style="-")
    arrow(ax, 74.6, 33, 84, 14, "0..1", style="-", offset=(1, 0))
    ax.text(60, -3, "Ngoài ra: packages · subscriptions · refunds · notifications · audit_logs", ha="center",
            fontsize=8.5, color="#475569")
    save(fig, "fig_erd")


# ---------------------------------------------------------------- 4. Máy trạng thái đơn ứng tuyển
def app_state():
    fig, ax = canvas(12, 5.2)
    st = [("NEW\nĐã nộp", 2), ("SCREENING\nSàng lọc", 21), ("INTERVIEW_\nINVITED", 40), ("INTERVIEW_\nSCHEDULED", 59),
          ("INTERVIEWED\nĐã PV", 78), ("OFFERED\nTrúng tuyển", 97)]
    W, Y = 14, 30
    for t, x in st:
        box(ax, x, Y, W, 9, t, "green" if "OFFERED" in t else "blue", 8.3, True)
    labels = ["HR", "HR", "ứng viên\nchọn slot", "HR ghi\nkết quả", "HR"]
    for i in range(5):
        arrow(ax, st[i][1] + W + 0.4, Y + 4.5, st[i + 1][1] - 0.4, Y + 4.5)
        ax.text((st[i][1] + W + st[i + 1][1]) / 2, Y + 10, labels[i], ha="center", fontsize=7.5)
    arrow(ax, 66, Y + 9.5, 47, Y + 9.5, "", rad=0.5, color="#7C3AED")
    ax.text(56.5, Y + 16.5, "HR hủy lịch → chọn lại", ha="center", fontsize=7.5, color="#7C3AED")
    ax.plot([9, 85], [22, 22], color="#E11D48", lw=1.2, ls="--")
    for _, x in st[:5]:
        ax.plot([x + 7, x + 7], [Y - 0.4, 22], color="#E11D48", lw=1.2, ls="--")
    arrow(ax, 30, 22, 30, 13.5, "", color="#E11D48", ls="--")
    ax.text(68, 23, "HR từ chối (mọi bước trước OFFERED)", fontsize=7.5, color="#E11D48")
    ax.plot([9.5, 66.5], [18, 18], color="#64748B", lw=1.2, ls=":")
    for _, x in st[:4]:
        ax.plot([x + 7.5, x + 7.5], [Y - 0.4, 18], color="#64748B", lw=1.2, ls=":")
    arrow(ax, 66.5, 18, 80, 13.5, "", color="#64748B", ls=":")
    ax.text(50, 14.5, "ứng viên rút đơn (trước khi phỏng vấn)", fontsize=7.5, color="#475569")
    box(ax, 20, 4, 20, 9, "REJECTED\nKhông phù hợp", "rose", 8.5, True)
    box(ax, 72, 4, 20, 9, "WITHDRAWN\nĐã rút đơn", "gray", 8.5, True)
    save(fig, "fig_app_state")


# ---------------------------------------------------------------- 5. Đặt lịch phỏng vấn
def slot_flow():
    fig, ax = canvas(12, 4.8)
    box(ax, 2, 22, 18, 10, "OPEN\n(trống)", "green", 10, True)
    box(ax, 44, 22, 18, 10, "HELD\n(giữ 10 phút)", "amber", 10, True)
    box(ax, 88, 22, 18, 10, "BOOKED\n(đã đặt)", "blue", 10, True)
    box(ax, 44, 1, 18, 8, "CANCELLED", "rose", 9, True)
    arrow(ax, 20, 29, 44, 29, "ứng viên chọn slot", offset=(0, 1))
    arrow(ax, 62, 29, 88, 29, "xác nhận trước hạn", offset=(0, 1))
    arrow(ax, 44, 24, 20, 24, "quá hạn → job định kỳ trả lại", offset=(0, -5.5))
    arrow(ax, 97, 22, 62, 6, "HR hủy / đơn bị từ chối", color="#E11D48", offset=(8, -1))
    ax.text(53, 44, "UPDATE interview_slots SET status='HELD', held_by=:uv, held_until=now()+10'\n"
                    "WHERE id=:slot AND (status='OPEN' OR (status='HELD' AND held_until < now()))  RETURNING id",
            ha="center", fontsize=8, family="Consolas",
            bbox=dict(fc="#F8FAFC", ec="#94A3B8", boxstyle="round,pad=0.6"))
    ax.text(53, 37, "Câu lệnh nguyên tử: 2 người bấm cùng lúc → chỉ 1 câu UPDATE trả về dòng, người kia nhận lỗi 409",
            ha="center", fontsize=8.5, color="#B45309")
    save(fig, "fig_slot_flow")


# ---------------------------------------------------------------- 6. Luồng thanh toán (sequence)
def payment_flow():
    fig, ax = canvas(12, 6.6)
    lanes = [("Người dùng", 11), ("Frontend", 33), ("Backend", 56), ("PostgreSQL", 80), ("SePay / Ngân hàng", 105)]
    for t, x in lanes:
        box(ax, x - 9, 58, 18, 6, t, "gray", 9, True)
        ax.plot([x, x], [2, 58], color="#CBD5E1", lw=1, ls="--")
    steps = [
        (11, 56, None, "1. Chọn gói → POST /api/orders", 52),
        (56, 80, None, "2. INSERT orders (PENDING, hạn 15')", 47),
        (56, 33, None, "3. mã đơn QTD000123 + ảnh VietQR", 42),
        (11, 105, None, "4. Quét QR, chuyển khoản (nội dung = mã đơn)", 37),
        (105, 56, None, "5. Webhook (Apikey) — có thể gửi lặp", 31),
        (56, 80, None, "6. INSERT tx (sepay_tx_id UNIQUE) → trùng thì bỏ qua", 26),
        (56, 80, None, "7. so mã đơn + số tiền; UPDATE orders→PAID WHERE status='PENDING'", 21),
        (56, 80, None, "8. kích hoạt gói (subscription / premium)", 16),
        (33, 56, None, "9. poll 3 giây/lần → thấy PAID", 10),
    ]
    for a_, b_, _, t, y in steps:
        arrow(ax, a_, y, b_, y, t, size=7.8, offset=(0, 0.4))
    ax.text(66, 3, "Sai số tiền → AMOUNT_MISMATCH · không thấy mã đơn → UNMATCHED · đơn đã hết hạn → LATE (hoàn tiền thủ công)\n"
                   "Job định kỳ: đơn PENDING quá hạn → EXPIRED · đối soát mỗi ngày 0h",
            ha="center", fontsize=8, color="#B45309")
    save(fig, "fig_payment_flow")


# ---------------------------------------------------------------- 7. Pipeline dữ liệu & AI
def ai_pipeline():
    fig, ax = canvas(12, 6.8)
    row1 = [("3.101 JD thật\n(LinkedIn · ITviec · TopCV)", "gray"), ("Làm sạch & chuẩn hóa\n→ 1.978 JD · 384 kỹ năng", "blue"),
            ("Sinh CV theo template\n3 CV/JD → 5.934 CV", "blue"), ("Chia train/val/test\ntheo JD (80/10/10)", "blue")]
    x = 2
    for i, (t, c) in enumerate(row1):
        box(ax, x, 50, 25, 10, t, c, 8.5, True)
        if i:
            arrow(ax, x - 4.6, 55, x - 0.3, 55)
        x += 30
    box(ax, 32, 28, 25, 11, "LLM review 5.252 cặp nhãn\n(Nemotron-3-Ultra)\n→ bỏ 365 bộ ba nhãn sai", "violet", 8.3)
    box(ax, 62, 28, 25, 11, "LLM viết lại CV tập test\n(Nemotron-3-Super)\n→ tập test_llm ~ CV thật", "violet", 8.3)
    box(ax, 92, 28, 25, 11, "Fine-tune bi-encoder\nmultilingual-e5-base\n(MNRL loss, ~4 phút)", "green", 8.3, True)
    arrow(ax, 104, 50, 104, 39.3)
    arrow(ax, 57.3, 33.5, 62, 33.5)
    arrow(ax, 44, 50, 44, 39.3, "")
    arrow(ax, 87.3, 33.5, 92, 33.5)
    box(ax, 2, 6, 25, 11, "Baseline so sánh\nBM25 · chỉ kỹ năng\ne5 chưa fine-tune", "gray", 8.3)
    box(ax, 32, 6, 25, 11, "Đánh giá\nNDCG@10 · MRR · Recall\n4 tập: test · test_llm\nđầu-cuối · nhãn LLM", "amber", 8.1)
    box(ax, 62, 6, 25, 11, "Dò trọng số hybrid\ntrên tập VAL\n(0,4 · 0,5 · 0,1)", "amber", 8.3)
    box(ax, 92, 6, 25, 11, "Triển khai vào web\nembed lại 7.912 JD/CV\nchỉ mục vector", "green", 8.3, True)
    arrow(ax, 104, 28, 104, 17.3)
    arrow(ax, 27.3, 11.5, 32, 11.5)
    arrow(ax, 57.3, 11.5, 62, 11.5)
    arrow(ax, 87.3, 11.5, 92, 11.5)
    arrow(ax, 104, 28, 50, 17.3, "", ls="--")
    save(fig, "fig_ai_pipeline")


# ---------------------------------------------------------------- 8. Chia dữ liệu
def split_fig():
    fig, ax = canvas(12, 4.2)
    total = 1978
    parts = [("train", 1584, "blue"), ("val", 197, "amber"), ("test", 197, "green")]
    x = 2
    for name, n, c in parts:
        w = 110 * n / total
        label = f"{name}\n{n} JD · {n * 3} CV" if n > 500 else f"{name}\n{n} JD\n{n * 3} CV"
        box(ax, x, 22, w - 1, 10, label, c, 9 if n > 500 else 8, True)
        x += w
    ax.text(2, 36, "Chia theo JD, phân tầng theo 16 nhóm nghề — mọi CV sinh cho 1 JD đi cùng JD đó (tránh rò rỉ)",
            fontsize=9, color="#334155")
    ax.text(2, 13, "• train → 3.168 bộ ba (JD, CV phù hợp, CV không/ít phù hợp); bản lọc bằng LLM còn 2.803\n"
                   "• val → chọn checkpoint tốt nhất và dò trọng số hybrid    • test → chỉ dùng để báo cáo kết quả cuối\n"
                   "• val/test chấm lại TOÀN BỘ ma trận JD × CV (197 × 591) bằng cùng một luật → không bỏ sót CV phù hợp với JD khác",
            fontsize=8.5, color="#334155", linespacing=1.6, va="top")
    save(fig, "fig_split")


# ---------------------------------------------------------------- 9. So khớp vector
def matching_fig():
    fig, ax = canvas(12, 6.4)
    box(ax, 2, 46, 22, 10, "CV (PDF/DOCX/văn bản)", "gray", 9, True)
    box(ax, 2, 20, 22, 10, "Tin tuyển dụng (JD)", "gray", 9, True)
    box(ax, 29, 46, 24, 10, "Trích xuất: kỹ năng, số năm,\nvị trí đã làm, ngành học", "blue", 8.5)
    box(ax, 29, 20, 24, 10, "Chuẩn hóa: chức danh, nhóm\nnghề, cấp bậc, số năm, kỹ năng", "blue", 8.5)
    box(ax, 58, 46, 22, 10, "Văn bản profile\n“Ứng viên: … Kỹ năng: …”", "amber", 8.5)
    box(ax, 58, 20, 22, 10, "Văn bản profile\n“Vị trí: … Kỹ năng yêu cầu: …”", "amber", 8.5)
    box(ax, 85, 33, 16, 10, "Encoder\n(e5 fine-tune)", "violet", 9, True)
    for y in (51, 25):
        arrow(ax, 24.3, y, 29, y)
        arrow(ax, 53.3, y, 58, y)
    arrow(ax, 80.3, 51, 85, 41)
    arrow(ax, 80.3, 25, 85, 35)
    box(ax, 104, 33, 15, 10, "Vector 768 chiều\n(chuẩn hóa độ dài 1)", "violet", 8)
    arrow(ax, 101.3, 38, 104, 38)
    ax.text(60, 8, "(1) Lọc nhanh: cosine = tích vô hướng 2 vector → lấy 200 ứng viên/tin gần nhất trong chỉ mục RAM\n"
                   "(2) Xếp hạng lại: điểm = 0,4 × ngữ nghĩa + 0,5 × độ phủ kỹ năng yêu cầu + 0,1 × mức đáp ứng kinh nghiệm\n"
                   "(3) Giải thích: kỹ năng khớp = JD ∩ CV · kỹ năng thiếu = JD − CV · kinh nghiệm = năm CV / năm yêu cầu",
            ha="center", fontsize=8.8, linespacing=1.7,
            bbox=dict(fc="#F8FAFC", ec="#94A3B8", boxstyle="round,pad=0.7"))
    save(fig, "fig_matching")


# ---------------------------------------------------------------- 10. Thống kê dữ liệu
def data_stats():
    jobs = [json.loads(l) for l in open(ROOT / "data/final/jobs.jsonl", encoding="utf-8")]
    vi = {"backend": "Backend", "software_engineer": "Software Eng.", "fullstack": "Full-stack", "frontend": "Frontend",
          "mobile": "Mobile", "qa_tester": "QA/Tester", "ai_ml": "AI/ML", "devops_cloud": "DevOps/Cloud",
          "embedded": "Nhúng", "data_engineer": "Data Eng.", "project_manager": "PM", "game": "Game",
          "security": "Bảo mật", "business_analyst": "BA", "blockchain": "Blockchain", "data_analyst": "Data Analyst"}
    roles = collections.Counter(j["role"] for j in jobs).most_common()
    skills = collections.Counter(s for j in jobs for s in j["skills"]).most_common(15)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), dpi=200)
    axs[0].barh([vi[r] for r, _ in roles][::-1], [n for _, n in roles][::-1], color="#3B6CF6")
    axs[0].set_title("Số JD theo nhóm nghề", fontsize=10, fontweight="bold")
    axs[1].barh([s for s, _ in skills][::-1], [n for _, n in skills][::-1], color="#059669")
    axs[1].set_title("15 kỹ năng xuất hiện nhiều nhất trong JD", fontsize=10, fontweight="bold")
    for a in axs:
        a.spines[["top", "right"]].set_visible(False)
        a.tick_params(labelsize=8)
        for c in a.containers:
            a.bar_label(c, fontsize=7, padding=2)
    fig.tight_layout()
    save(fig, "fig_data_stats")


# ---------------------------------------------------------------- 11. Ma trận đồng thuận nhãn
def agreement():
    rows = [json.loads(l) for l in open(ROOT / "data/llm/label_reviews.jsonl", encoding="utf-8")]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), dpi=200)
    for a, src, title in ((axs[0], "train_pair", "Cặp train (4.752)"), (axs[1], "annotation", "File gán nhãn tay (500)")):
        m = [[0] * 3 for _ in range(3)]
        for r in rows:
            if r["source"] == src:
                m[r["rule_label"]][r["llm_label"]] += 1
        a.imshow(m, cmap="Blues")
        for i in range(3):
            for j in range(3):
                a.text(j, i, m[i][j], ha="center", va="center", fontsize=10,
                       color="white" if m[i][j] > max(map(max, m)) / 2 else "#0F172A")
        a.set_xticks(range(3), ["0", "1", "2"])
        a.set_yticks(range(3), ["0", "1", "2"])
        a.set_xlabel("Nhãn LLM")
        a.set_ylabel("Nhãn luật")
        agree = sum(m[i][i] for i in range(3)) / sum(map(sum, m))
        a.set_title(f"{title} — đồng ý {agree:.1%}", fontsize=10, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig_agreement")


# ---------------------------------------------------------------- 12. Kết quả
def results_fig():
    t = json.load(open(ROOT / "results/test_profile.json"))["results"]
    e2e = json.load(open(ROOT / "results/end2end_test_llm.json"))
    llm = json.load(open(ROOT / "results/llmlabel_profile.json"))["results"]
    ft = "models/cvjd-e5-base-profile-clean"
    methods = [("BM25", "bm25"), ("Chỉ kỹ năng", "skill"), ("e5 gốc", "e5-base"), ("e5 fine-tune", ft),
               ("e5 gốc + hybrid", "e5-base+hybrid"), ("e5 fine-tune + hybrid", ft + "+hybrid")]
    tuned = {"e5-base+hybrid": json.load(open(ROOT / "results/hybrid_e5-base.json"))["test"]["ndcg@10"],
             ft + "+hybrid": json.load(open(ROOT / "results/hybrid_cvjd-e5-base-profile-clean.json"))["test"]["ndcg@10"]}
    groups = [("Test (template)", lambda k: tuned.get(k, t[k]["jd2cv"]["ndcg@10"] if k in t else 0)),
              ("Đầu-cuối trên CV do LLM viết", lambda k: e2e[k]["ndcg@10"]),
              ("Nhãn do LLM chấm", lambda k: llm[k]["ndcg@10"])]
    colors = ["#94A3B8", "#CBD5E1", "#FCA5A5", "#2553E6", "#FDBA74", "#059669"]
    fig, ax = plt.subplots(figsize=(12, 4.4), dpi=200)
    w = 0.13
    for i, (label, key) in enumerate(methods):
        xs = [g + (i - 2.5) * w for g in range(len(groups))]
        ys = [f(key) for _, f in groups]
        bars = ax.bar(xs, ys, w, label=label, color=colors[i])
        ax.bar_label(bars, labels=[f"{y:.2f}" for y in ys], fontsize=6.5, padding=1)
    ax.set_xticks(range(len(groups)), [g for g, _ in groups])
    ax.set_ylabel("NDCG@10")
    ax.set_ylim(0.4, 1.02)
    ax.legend(ncol=6, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, 1.13), frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "fig_results")


def training_fig():
    names = [("A. profile · dữ liệu gốc", 0.6577, 0.8388), ("B. profile · lọc bằng LLM", 0.6577, 0.8467),
             ("C. toàn văn · lọc bằng LLM", 0.3105, 0.6762)]
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=200)
    y = range(len(names))
    ax.barh([i + 0.2 for i in y], [b for _, b, _ in names], 0.38, color="#CBD5E1", label="Trước fine-tune")
    ax.barh([i - 0.2 for i in y], [a for _, _, a in names], 0.38, color="#2553E6", label="Sau fine-tune")
    for i, (_, b, a) in enumerate(names):
        ax.text(b + 0.01, i + 0.2, f"{b:.3f}", va="center", fontsize=8)
        ax.text(a + 0.01, i - 0.2, f"{a:.3f}", va="center", fontsize=8, color="#1D41C4", fontweight="bold")
    ax.set_yticks(list(y), [n for n, _, _ in names])
    ax.invert_yaxis()
    ax.set_xlabel("NDCG@10 trên tập val")
    ax.set_xlim(0, 1)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "fig_training")


if __name__ == "__main__":
    for f in (architecture, usecases, erd, app_state, slot_flow, payment_flow, ai_pipeline, split_fig, matching_fig,
              data_stats, agreement, results_fig, training_fig):
        f()
