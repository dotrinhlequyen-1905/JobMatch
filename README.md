# JobMatch — hệ thống tuyển dụng và so khớp CV–Job

Tên chính thức của hệ thống trong toàn bộ dự án và tài liệu là **JobMatch**.

Dự án gồm một backend FastAPI và một frontend React. Cơ sở thiết kế là tài liệu đặc tả JobMatch, đặc biệt các phần kiến trúc, API, quy tắc nghiệp vụ và giao diện đánh giá CV.

Mô-đun AI đã hoàn thành dùng E5/cosine/hybrid. Chương 5 của SRS JobMatch trình bày đầy đủ dữ liệu, phương pháp, huấn luyện, thiết kế thực nghiệm, bảng kết quả và phân tích; Cross-Encoder chỉ là hướng mở rộng.

Các tài liệu đồ án (SRS JobMatch, báo cáo thực nghiệm, sổ tay mô-đun AI) được nộp riêng, không kèm trong repo này.

## Cấu trúc

```text
doanchuyennganh/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # HTTP, kiểm tra dữ liệu vào và phân quyền
│   │   ├── schemas/       # DTO theo tài nguyên/nghiệp vụ
│   │   ├── services/      # Quy tắc nghiệp vụ và ranh giới transaction
│   │   ├── repositories/ # Truy vấn SQLAlchemy/pgvector
│   │   ├── ai/           # Parser, embedding, reranking, skill gap, đánh giá CV
│   │   ├── core/         # Database, JWT/RBAC, thời gian, kiểu vector
│   │   ├── tasks/        # Celery worker và lịch Celery Beat
│   │   ├── models.py     # Các bảng ORM đang được sử dụng
│   │   ├── state_machines.py
│   │   ├── config.py
│   │   └── main.py
│   ├── alembic/          # Migration giữ dữ liệu cũ
│   ├── scripts/seed.py   # Nạp demo hoặc tính lại vector
│   └── tests/
├── frontend/             # React + TypeScript + Vite + Tailwind
├── nginx/                # Gateway và phục vụ SPA
├── data_pipeline/        # Làm sạch, sinh CV, chia tập, xuất dữ liệu
├── ml/                   # Huấn luyện và đánh giá mô hình
├── llm/                  # Thí nghiệm bổ sung/kiểm tra dữ liệu bằng OpenRouter
├── data/                 # Dữ liệu nghiên cứu đã giữ lại, phần lớn không đưa lên Git
├── models/               # Checkpoint đã giữ lại, không đưa lên Git
├── results/              # Kết quả thực nghiệm đã giữ lại
├── e2e/                  # Kịch bản kiểm tra giao diện
├── scripts/              # Xuất hợp đồng API và kiểm tra tài sản đã di chuyển
└── docs/                 # Kiến trúc, triển khai, đối chiếu đặc tả và tài liệu nguồn
```

Luồng chính: React → Nginx → FastAPI → Service → Repository → PostgreSQL/pgvector. FastAPI giao việc tính vector và xử lý định kỳ cho Celery qua Redis.

## Chạy bằng Docker Compose

Cần Docker với Compose hỗ trợ `env_file.required` và khoảng trống đủ cho thư viện/model AI. Tại thư mục gốc, tạo `.env` từ `.env.example` nếu chưa có; giữ lại giá trị cấu hình cá nhân trong file hiện có. Điền cấu hình database, JWT, SePay và model phù hợp.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
```

Compose chạy PostgreSQL có pgvector, Redis, migration, API, Celery worker, Celery Beat, frontend và Nginx. Truy cập `http://localhost`, API docs tại `http://localhost/docs`.

Chế độ phát triển:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Frontend phát triển ở `http://localhost:5173`. [Hướng dẫn triển khai](docs/deployment.md) có các lệnh chạy trực tiếp trên Windows, nạp demo và nâng cấp database cũ.

Gói Premium ứng viên gồm 1 tháng (99.000đ), 3 tháng (249.000đ) và 12 tháng (899.000đ). Với database đã có dữ liệu, đồng bộ danh mục mà vẫn giữ số tiền và quyền lợi của đơn cũ:

```powershell
docker compose exec backend python scripts/sync_premium_packages.py
```

Mọi đơn (Premium ứng viên và gói đăng tin HR) thanh toán bằng mã VietQR do SePay sinh (`SEPAY_BANK`, `SEPAY_ACCOUNT`, nội dung chuyển khoản là mã đơn); đơn được xác nhận tự động khi SePay gọi `POST /api/v1/webhooks/sepay`. Khi `PAYMENT_DEMO_ENABLED=true` (mặc định), trang thanh toán vẫn hiện QR thật và có thêm nút **Giả lập chuyển khoản thành công / thiếu tiền**: hệ thống tạo payload đúng định dạng webhook SePay và xử lý qua chính luồng xác nhận thật (idempotent, đối chiếu mã đơn và số tiền), không cần chuyển tiền. Đặt `PAYMENT_DEMO_ENABLED=false` khi chạy thật.

## Kiểm tra

Cài Python 3.11 trở lên và Node.js 24. Từ thư mục gốc, sau khi kích hoạt môi trường Python:

```powershell
python -m pip install -e './backend[dev]'
python -m pytest backend/tests -q
python -m ruff check backend/app
python scripts/export_api.py --check
Set-Location frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run build
```

Kiểm thử mặc định dùng SQLite riêng, embedder `hashing`, không cần tải model hoặc gọi SePay. `TEST_DATABASE_URL` cho phép chạy cùng các luồng nghiệp vụ trên PostgreSQL có pgvector; tên database phải chứa `test`. CI đã được cấu hình dùng PostgreSQL cho backend.

## Tài liệu cần đọc

- [Kiến trúc thống nhất](docs/architecture.md): trách nhiệm các lớp và luồng xử lý.
- [Đối chiếu với Word](docs/specification-alignment.md): phần đã thực hiện và chức năng còn thiếu.
- [Mô hình dữ liệu](docs/erd.md) và [pipeline AI](docs/ai-pipeline.md).
- [Hợp đồng API sinh từ FastAPI](docs/api-spec.yaml).

Các yêu cầu FR-1 đến FR-8 trong đặc tả đã được triển khai (xác minh email, refresh token, khôi phục mật khẩu, hồ sơ ứng viên, tin nháp/mở lại, hủy/đổi lịch và nhắc lịch phỏng vấn, trạng thái chờ đối soát, báo cáo vi phạm, bảng kỹ năng chuẩn hóa). Giới hạn còn lại và giả định tích hợp được ghi trong [bảng đối chiếu](docs/specification-alignment.md).
