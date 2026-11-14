<p align="center">
  <img src="frontend/public/images/jobmatch-logo.png" alt="JobMatch" width="320">
</p>

<h3 align="center">Tìm đúng việc · Tuyển đúng người</h3>

<p align="center">
  Nền tảng tuyển dụng thông minh hai chiều, dùng AI để so khớp CV với tin tuyển dụng
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
</p>

<p align="center">
  <img src="docs/screenshots/home.jpg" alt="Trang chủ JobMatch" width="900">
</p>

---

## JobMatch là gì?

Trên các trang tuyển dụng phổ biến, ứng viên phải tự lọc hàng trăm tin. Nhà tuyển dụng thì đọc thủ công từng CV. Việc tìm kiếm chủ yếu dựa vào từ khóa, nên "ReactJS" và "React.js" có thể bị xem là hai kỹ năng khác nhau. Một CV tốt vẫn có thể bị bỏ sót chỉ vì cách viết khác đi.

**JobMatch** giải quyết vấn đề này bằng cách để AI **hiểu nội dung** của CV và tin tuyển dụng, rồi gợi ý theo **cả hai chiều**:

- **Ứng viên** nhận danh sách việc làm phù hợp nhất với CV của mình, kèm giải thích vì sao phù hợp và còn thiếu kỹ năng gì.
- **Nhà tuyển dụng** nhận danh sách ứng viên tiềm năng cho từng tin, kể cả những người chưa nộp đơn.

Toàn bộ quy trình tuyển dụng nằm trên một nền tảng, từ đăng tin, ứng tuyển, đặt lịch phỏng vấn đến thanh toán.

## Tính năng nổi bật

### Dành cho ứng viên
- **Tải CV lên, AI tự đọc:** hệ thống trích xuất thông tin cá nhân, kinh nghiệm, học vấn và kỹ năng từ file PDF/DOCX.
- **Gợi ý việc làm bằng AI:** việc làm được xếp hạng theo mức độ phù hợp với CV, có phần trăm phù hợp rõ ràng.
- **Phân tích khoảng cách kỹ năng:** cho biết kỹ năng nào đã đáp ứng, kỹ năng nào còn thiếu so với từng vị trí.
- **Đánh giá CV và gợi ý cải thiện:** chấm điểm mức độ đầy đủ của CV và chỉ ra phần cần bổ sung.
- **Ứng tuyển và tự chọn lịch phỏng vấn:** chọn khung giờ trống do nhà tuyển dụng mở. Khung giờ được giữ chỗ 10 phút để không bị người khác chọn trùng.
- **Gói Premium (1, 3 hoặc 12 tháng):** mở khóa đánh giá CV chuyên sâu, gợi ý cải thiện và đối chiếu với vị trí tuyển dụng, thanh toán bằng mã VietQR.

### Dành cho nhà tuyển dụng
- **Đăng và quản lý tin tuyển dụng:** lưu nháp, đăng, đóng hoặc mở lại tin.
- **Ứng viên AI gợi ý:** xem ngay những ứng viên phù hợp nhất cho từng tin, kèm kỹ năng khớp và kỹ năng thiếu.
- **Quản lý hồ sơ ứng tuyển:** chuyển trạng thái từ sàng lọc đến phỏng vấn và kết quả, ứng viên được thông báo tự động.
- **Mở lịch phỏng vấn:** tạo các khung giờ để ứng viên tự đặt, không cần trao đổi qua lại.
- **Gói đăng tin:** mua thêm lượt đăng tin, thanh toán tự động xác nhận qua SePay.

### Dành cho quản trị viên
- **Bảng thống kê:** người dùng, tin tuyển dụng, hồ sơ, doanh thu theo thời gian.
- **Kiểm duyệt:** duyệt công ty, xử lý báo cáo vi phạm.
- **Đối soát thanh toán:** theo dõi giao dịch, xử lý đơn chờ đối soát và yêu cầu hoàn tiền.

## AI so khớp hoạt động thế nào?

```text
  CV / Tin tuyển dụng
          │
          ▼
  ① Đọc hiểu      →  trích xuất kỹ năng, kinh nghiệm, vị trí
          │
          ▼
  ② Hiểu ngữ nghĩa →  mô hình E5 (đã tinh chỉnh cho tiếng Việt và CV–JD)
          │            chuyển nội dung thành vector để so sánh ý nghĩa
          ▼
  ③ Tìm nhanh      →  lọc ra 200 kết quả gần nhất trong cơ sở dữ liệu vector
          │
          ▼
  ④ Chấm điểm      →  kết hợp: độ giống ngữ nghĩa + mức phủ kỹ năng + kinh nghiệm
          │
          ▼
  Danh sách gợi ý  +  giải thích kỹ năng đã có / còn thiếu
```

Mô hình được huấn luyện và đánh giá trên **1.978 tin tuyển dụng**, **5.934 CV** thuộc **16 nhóm ngành**, với bộ từ điển **384 kỹ năng**.

| Chỉ số | Kết quả |
|---|---|
| Độ chính xác xếp hạng (NDCG@10), mô hình gốc → sau tinh chỉnh | 0,630 → **0,842** (tăng 34%) |
| NDCG@10 khi kết hợp chấm điểm kỹ năng và kinh nghiệm | **0,905** |
| Không bỏ sót kết quả phù hợp trong Top-50 (Recall@50) | **0,999** |
| Độ chính xác trích xuất thông tin từ CV (F1) | **0,951** |

## Giao diện

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/recommendations.jpg" alt="Gợi ý việc làm"><br><sub><b>Gợi ý việc làm bằng AI</b>, xếp hạng theo mức độ phù hợp</sub></td>
    <td width="50%"><img src="docs/screenshots/job-match.jpg" alt="Phân tích phù hợp"><br><sub><b>Phân tích mức độ phù hợp</b>, kỹ năng đáp ứng và còn thiếu</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/cv-evaluation.jpg" alt="Đánh giá CV"><br><sub><b>Đánh giá CV</b>, chấm điểm và gợi ý cải thiện</sub></td>
    <td><img src="docs/screenshots/hr-ai-candidates.jpg" alt="Ứng viên AI gợi ý"><br><sub><b>Ứng viên AI gợi ý</b> cho nhà tuyển dụng</sub></td>
  </tr>
  <tr>
    <td colspan="2"><img src="docs/screenshots/admin-dashboard.jpg" alt="Thống kê quản trị"><br><sub><b>Bảng thống kê</b> dành cho quản trị viên</sub></td>
  </tr>
</table>

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Giao diện | React, TypeScript, Vite, Tailwind CSS |
| Máy chủ | FastAPI (Python), Celery, Redis |
| Cơ sở dữ liệu | PostgreSQL + pgvector (tìm kiếm vector) |
| AI | Sentence Transformers, mô hình multilingual-E5 tinh chỉnh |
| Thanh toán | VietQR qua SePay (xác nhận tự động bằng webhook) |
| Triển khai | Docker Compose, Nginx, GitHub Actions |

## Chạy thử

Cần cài [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/dotrinhlequyen-1905/JobMatch.git
cd JobMatch
cp .env.example .env
docker compose up -d --build
docker compose exec backend python scripts/seed.py   # nạp dữ liệu mẫu
```

Mở trình duyệt tại **http://localhost** và đăng nhập bằng một trong các tài khoản mẫu (mật khẩu `123456`):

| Vai trò | Email |
|---|---|
| Ứng viên | `candidate@demo.vn` |
| Nhà tuyển dụng | `hr@demo.vn` |
| Quản trị viên | `admin@demo.vn` |

> **Lưu ý:** mô hình AI đã tinh chỉnh không kèm trong repo vì dung lượng lớn. Để chạy thử nhanh, trong file `.env` đặt `EMBED_MODEL=intfloat/multilingual-e5-base` (tự tải mô hình gốc) hoặc `EMBED_MODEL=hashing` (không cần tải mô hình). Ở chế độ demo, trang thanh toán có nút giả lập chuyển khoản nên không cần chuyển tiền thật.

Hướng dẫn chi tiết hơn (chạy không dùng Docker, cấu hình thanh toán, kiểm thử) nằm trong [docs/deployment.md](docs/deployment.md).

## Testing

**Backend (pytest):** mặc định dùng SQLite tạm, không cần Docker.

```bash
pip install -e "backend[dev]"
python -m pytest backend/tests -q
```

**Giao diện end-to-end (Playwright):** cần backend chạy ở `:8000`, frontend dev server ở `:5173` (`cd frontend && npm run dev`) và database đã nạp dữ liệu mẫu.

```bash
pip install playwright
playwright install chromium
python e2e/smoke_ui.py      # đi hết luồng chính của 3 vai trò, ảnh chụp lưu ở e2e/screenshots/
python e2e/mobile_check.py  # chụp các trang chính ở khổ điện thoại (390x844), báo trang bị tràn ngang
```

## Tài liệu kỹ thuật

- [Kiến trúc hệ thống](docs/architecture.md)
- [Pipeline AI](docs/ai-pipeline.md)
- [Mô hình dữ liệu](docs/erd.md)
- [Đặc tả API](docs/api-spec.yaml)
- [Triển khai và vận hành](docs/deployment.md)

## Tác giả

Đồ án chuyên ngành, ngành Kỹ thuật phần mềm, Trường Đại học Phenikaa.

- **Sinh viên thực hiện:** Đỗ Trịnh Lệ Quyên
- **Giảng viên hướng dẫn:** TS. Mai Thuý Nga
- **Liên hệ:** quyendotrinhle@gmail.com
