# Chạy dự án và nâng cấp dữ liệu

Tất cả lệnh bên dưới chạy từ root trừ khi ghi rõ. File `backend/pyproject.toml` là nguồn dependency Python; `frontend/package-lock.json` khóa dependency frontend. `.env` tại root được đọc trước, `backend/.env` ghi đè khi chạy Python trực tiếp; biến môi trường của tiến trình có ưu tiên cao nhất.

## Docker Compose

Tạo `.env` nếu chưa có, sau đó điền các thiết lập trong `.env.example`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose logs -f backend celery-worker celery-beat
```

Service `migrate` chạy `alembic upgrade head` trước API/worker/beat. Database và Redis chỉ mở cổng trên loopback. Nginx phục vụ frontend và chuyển tiếp `/api/v1`, `/docs`, `/openapi.json`. Volume `pgdata`, `redisdata`, `uploads` giữ dữ liệu khi khởi động lại. Thư mục `models` và `data` được mount chỉ đọc.

Các địa chỉ: website `http://localhost`; Swagger `http://localhost/docs`; API trực tiếp để debug `http://127.0.0.1:8000/api/v1`.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
docker compose down
```

Chế độ phát triển mở Vite tại `http://localhost:5173` và bật reload API. Chỉ chạy một Celery Beat cho mỗi môi trường để tránh gửi lịch công việc trùng.

## Chạy trực tiếp trên Windows

Cần Python 3.11+, Node.js 24, PostgreSQL có extension pgvector và Redis. Có thể dùng Compose để chạy riêng database/broker:

```powershell
docker compose up -d db redis
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e './backend[ai,dev]'
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Nếu PowerShell hạn chế chạy script, dùng trực tiếp `.venv\Scripts\python.exe` và `npm.cmd`; không cần thay execution policy. Máy dùng `uv` có thể thay bước cài dependency bằng `uv pip install --python .venv\Scripts\python.exe -e './backend[ai,dev]'`.

Trong hai terminal khác tại root:

```powershell
# Celery trên Windows dùng pool solo; Compose/Linux dùng pool mặc định.
.venv\Scripts\python.exe -m celery -A app.tasks.celery_app:celery_app worker --pool=solo --loglevel=info
```

```powershell
.venv\Scripts\python.exe -m celery -A app.tasks.celery_app:celery_app beat --loglevel=info
```

Frontend:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Vite tự proxy API đến `127.0.0.1:8000`. Không cần sửa đường dẫn API trong các trang.

## Email, phiên đăng nhập và tác vụ nền

Xác minh email và xác nhận/nhắc lịch phỏng vấn được gửi qua Celery sau khi transaction commit. Email đặt lại mật khẩu được gửi trực tiếp qua SMTP sau khi lưu token, không phụ thuộc Redis/worker; lỗi gửi được trả về giao diện để người dùng thử lại. Cấu hình SMTP trong `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<app password>
SMTP_FROM=JobMatch <you@gmail.com>
FRONTEND_URL=http://localhost
```

Để trống `SMTP_HOST` khi phát triển: email xác minh và thông báo được ghi ở mức WARNING vào log backend hoặc worker. Chức năng quên mật khẩu chỉ dùng email thật và yêu cầu SMTP hoạt động; không hiển thị token hoặc liên kết đặt lại trong phản hồi API hay giao diện. Nếu SMTP chưa được cấu hình hoặc gửi thất bại, API trả lỗi dịch vụ chưa khả dụng thay vì báo đã gửi email. `FRONTEND_URL` phải trỏ tới địa chỉ website mà người dùng truy cập.

### Gmail với mật khẩu ứng dụng

Bật xác minh hai bước cho tài khoản Google, sau đó tạo mật khẩu ứng dụng tại https://myaccount.google.com/apppasswords. Google yêu cầu xác minh hai bước để tạo mật khẩu ứng dụng: https://support.google.com/mail/answer/185833. Điền cấu hình trong `.env` ở thư mục gốc, không đưa thông tin đăng nhập vào Git:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=dia_chi_cua_ban@gmail.com
SMTP_PASSWORD=mat_khau_ung_dung_16_ky_tu
SMTP_TLS=true
SMTP_FROM=
FRONTEND_URL=http://127.0.0.1:5173
```

`SMTP_PASSWORD` là mật khẩu ứng dụng, không phải mật khẩu đăng nhập Gmail. Để trống `SMTP_FROM` để tự dùng địa chỉ `SMTP_USER` với tên hiển thị JobMatch. Cổng 587 sử dụng STARTTLS và kiểm tra chứng chỉ TLS theo cấu hình Gmail: https://support.google.com/mail/answer/7104828. Chạy qua Docker/Nginx dùng `FRONTEND_URL=http://localhost`; website công khai dùng địa chỉ HTTPS thực tế. Cấu hình trong `backend/.env` ghi đè `.env` khi chạy trực tiếp trên máy, nên tránh để thông tin SMTP khác nhau trong hai tệp.

Kiểm tra cấu hình, rồi kiểm tra kết nối và đăng nhập SMTP mà không gửi email:

```powershell
.venv\Scripts\python.exe backend/scripts/check_smtp.py
.venv\Scripts\python.exe backend/scripts/check_smtp.py --connect
```

Sau khi thay `.env`, khởi động lại API và worker. Với Docker, tạo lại các container dùng cấu hình backend để nạp biến mới:

```powershell
docker compose up -d --force-recreate backend celery-worker celery-beat
```

Đặt `REQUIRE_EMAIL_VERIFICATION=true` để chặn đăng nhập khi chưa xác minh; tài khoản có sẵn trước migration `0003` và tài khoản demo được coi là đã xác minh.

Access token JWT hết hạn sau `JWT_EXPIRE_MINUTES`; frontend tự gọi `/auth/refresh` bằng refresh token (`REFRESH_TOKEN_DAYS`). Mỗi refresh token chỉ dùng một lần; dùng lại token cũ sẽ thu hồi mọi phiên của tài khoản.

Celery Beat chạy: hết hạn đơn/khung giờ/tin (mỗi phút), tính lại vector đang chờ (5 phút), nhắc lịch phỏng vấn trong `INTERVIEW_REMINDER_HOURS` giờ tới (15 phút) và đối soát lúc 00:00. Khi có `SEPAY_API_TOKEN`, đối soát lấy lịch sử giao dịch 2 ngày gần nhất từ API SePay và ghi nhận giao dịch bị thiếu webhook.

## Model AI

`EMBED_MODEL` nhận tên model Sentence Transformers hoặc đường dẫn tương đối từ root. Ví dụ `models/cvjd-e5-base-profile-clean` dùng checkpoint đã giữ lại. `CROSS_ENCODER_MODEL` là tên/đường dẫn Cross-Encoder. API và worker cần cùng cấu hình model; sau khi đổi model phải tính lại vector.

Mặc định không tự chuyển sang hashing nếu không tải được model. `EMBED_MODEL=hashing`, `CROSS_ENCODER_MODEL=` chỉ dành cho kiểm thử chức năng hoặc chế độ demo được chủ động cấu hình. Khi dùng model thật, cài extra `[ai]`; lần đầu có thể cần tải Cross-Encoder. Các checkpoint cũ không bao gồm một Cross-Encoder đã fine-tune.

## Database mới và database cũ

Database mới:

```powershell
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

Database cũ chưa có Alembic: sao lưu database trước; đối chiếu các bảng với migration `0001_imported_schema.py`. Chỉ khi database đúng schema cũ này mới đánh dấu baseline rồi nâng cấp:

```powershell
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini stamp 0001
.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.venv\Scripts\python.exe backend/scripts/seed.py --reembed
```

`stamp` chỉ đánh dấu phiên bản, không tạo bảng. Không dùng `stamp 0001` với database trống hoặc schema khác. Migration `0002` giữ vector cũ khi đổi binary sang pgvector, bổ sung trạng thái worker và thay unique ứng tuyển bằng unique cho đơn còn hoạt động. Vector cũ mang nhãn `legacy`; cần `--reembed` theo model đã chọn trước khi sử dụng để so khớp. Các bản ghi người dùng, CV, Job và thanh toán được giữ.

Migration tạo HNSW cho vector 768 chiều. Model có số chiều khác vẫn tìm được bằng truy vấn pgvector có kiểm tra số chiều, nhưng cần thêm migration chỉ mục tương ứng để tối ưu. Downgrade bị chặn nếu đã có nhiều đơn ứng tuyển lịch sử cho cùng ứng viên/Job, vì schema cũ không chứa được các bản ghi này.

Không có thao tác kết nối/nâng cấp database thực tế của người dùng trong lần hợp nhất nguồn mã. Đường chuyển đổi đã được kiểm thử trên database SQLite độc lập; CI được cấu hình kiểm tra luồng ứng dụng với PostgreSQL/pgvector.

## Nạp demo

Sau migration, với database trống và dataset `data/final` hiện có:

```powershell
.venv\Scripts\python.exe backend/scripts/seed.py
# Hoặc trong container:
docker compose exec backend python scripts/seed.py
```

Seeder từ chối nếu database đã có dữ liệu. `--reset` là tùy chọn chủ động xóa dữ liệu ứng dụng rồi nạp demo; không tự xóa khi chạy lệnh mặc định. `--reembed` chỉ tính lại vector. Seeder không drop schema hoặc bảng Alembic nên giữ được chỉ mục migration.

Tài khoản demo sau khi nạp: `admin@demo.vn`, `hr@demo.vn`, `candidate@demo.vn`, mật khẩu `123456`. Đây là dữ liệu phục vụ kiểm tra/demo.

## Xác nhận thay đổi

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv\Scripts\python.exe -m ruff check backend/app
.venv\Scripts\python.exe scripts/export_api.py --check
```

Không đặt `TEST_DATABASE_URL` vào database đang dùng cho ứng dụng; fixture xóa/tạo bảng trong database kiểm thử. Backend CI dùng database `recruit_ai_test` với pgvector. Bộ kiểm thử dùng hashing và Cross-Encoder giả lập để kiểm tra nghiệp vụ/điều phối; chất lượng model thật cần đánh giá riêng.
