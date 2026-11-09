# Đối chiếu mã nguồn với tài liệu đặc tả

Đối chiếu theo đặc tả JobMatch, gồm kiến trúc, quy tắc BR, API và các cập nhật đánh giá CV Premium cuối tài liệu. “Có” mô tả mã nguồn hiện tại; không đồng nghĩa đã kiểm thử dịch vụ bên ngoài/model thật.

Phần AI được trình bày đầy đủ trong Chương 5 của SRS: dữ liệu, huấn luyện, E5/cosine/hybrid, thiết kế thực nghiệm, kết quả và phân tích. Chương 3 của báo cáo thực nghiệm JobMatch là bản nháp dùng để biên soạn; SRS không yêu cầu người đọc tra bản nháp để hiểu phần AI. Cross-Encoder chỉ là hướng mở rộng. Các kiểm chứng pgvector, worker và API được tách khỏi thực nghiệm NumPy.

## Kiến trúc

| Yêu cầu trong Word | Kết quả hợp nhất |
|---|---|
| FastAPI backend Python và React SPA | Một `backend/app` và một `frontend/src`, bỏ hai cây chạy song song |
| Controller/API → Service → Repository → ORM | Đã tách route, schema, service, query; kiểm thử ranh giới các lớp |
| PostgreSQL + pgvector | Kiểu vector, truy vấn cosine có lọc chiều/model, migration binary→vector, chỉ mục HNSW 768 chiều |
| Celery + Redis + lịch công việc | Worker/Beat tách API; tính vector sau commit, xử lý hết hạn, đối soát 00:00 Việt Nam |
| E5/cosine + xếp hạng hybrid | Dữ liệu, huấn luyện và kết quả đánh giá được trình bày tại Chương 5 SRS; checkpoint B dùng 0,40/0,50/0,10, floor 0. Source web còn nhánh CE tùy chọn; cấu hình theo phương pháp tại Chương 5 đặt CROSS_ENCODER_MODEL rỗng |
| Alembic, Docker Compose, Nginx | Đã thay cấu hình mẫu bằng cấu hình trỏ đến source thật và thứ tự migration trước ứng dụng |
| Mã nghiên cứu/dữ liệu được quản lý riêng | `data_pipeline`, `ml`, `llm`, `data`, `models`, `results` tại root |

## API cốt lõi

Các đường dẫn dưới đây có prefix `/api/v1`. Hợp đồng đầy đủ sinh từ ứng dụng ở [api-spec.yaml](api-spec.yaml).

| API trong đặc tả | Hiện trạng |
|---|---|
| `POST /auth/register`, `POST /auth/login` | Có JWT access và RBAC; đăng ký gửi email xác minh, HR được tạo hồ sơ công ty chờ duyệt; đăng nhập ghi nhật ký `LOGIN` |
| `POST /auth/refresh`, `POST /auth/logout` | Có refresh token xoay vòng (chỉ lưu SHA-256), dùng lại token cũ thu hồi toàn bộ phiên; đăng xuất thu hồi phía server |
| `POST /auth/forgot-password`, `POST /auth/reset-password` | Có token một lần, hạn 30 phút, gửi qua email; phản hồi không lộ email đã đăng ký; đặt lại thu hồi mọi phiên |
| `POST /auth/verify-email`, `POST /auth/resend-verification` | Có; `REQUIRE_EMAIL_VERIFICATION=true` chặn đăng nhập khi chưa xác minh |
| `GET/PUT /users/me`, `POST /users/me/avatar` | Có; đổi mật khẩu bắt buộc mật khẩu hiện tại và cấp phiên mới; ảnh đại diện kiểm tra định dạng/kích thước |
| `GET/PUT /users/me/profile` | Có hồ sơ nghề nghiệp ứng viên; ẩn hồ sơ thì CV không xuất hiện trong gợi ý ứng viên cho HR (FR-2.4) |
| `POST/GET /cvs`, `GET /cvs/{id}` | Có upload/parse/quản lý CV và kiểm tra sở hữu |
| `POST /companies` | Có tạo hồ sơ cho HR chưa có công ty; HR đã được tạo công ty khi đăng ký dùng `PUT /companies/me` |
| `POST/GET /jobs`, `GET /jobs/{id}` | Có; chỉ công khai tin còn hiệu lực/đã duyệt |
| `PATCH /jobs/{id}/status` | Có: đóng tin, gửi duyệt bản nháp (trừ lượt đăng khi gửi), mở lại tin đã đóng (duyệt lại, có thể gia hạn); HR không tự công bố được |
| `POST /jobs` với `submit=false` | Lưu tin ở trạng thái Nháp (FR-3.1), chưa dùng lượt đăng |
| `GET /jobs/owned` | Có số lượt xem (không tính chủ tin/admin), số hồ sơ và điểm phù hợp trung bình (FR-3.5) |
| `GET /matching/jobs?cv_id=...` | Có cho ứng viên; gợi ý cơ bản miễn phí |
| `GET /jobs/{id}/candidates` | Có cho HR sở hữu tin, ẩn danh khi chưa có ứng tuyển |
| `GET /matching/gap` | Có cho ứng viên sở hữu CV và cho HR với CV đã ứng tuyển vào tin của mình (BR-20) |
| `GET /matching/cv-evaluation` | Có Premium; điểm CV, điểm Job và bằng chứng/gợi ý tách biệt |
| `POST/GET /applications` | Có; một đơn còn hoạt động trên mỗi cặp ứng viên/Job |
| `PATCH /applications/{id}/status` | Có chuyển trạng thái theo vai trò và lưu lịch sử |
| `POST /applications/{id}/withdraw` | Có trước trạng thái kết quả cuối cùng |
| `POST /jobs/{id}/interview-slots` | Có cho HR sở hữu tin |
| `POST /interview-slots/{id}/hold`, `POST /interview-slots/{id}/book` | Có hold có hạn và xác nhận nguyên tử; email xác nhận cho ứng viên |
| `POST /interview-slots/{id}/cancel` | HR hủy lịch; ứng viên hủy chỗ giữ hoặc lịch đã đặt (trước ít nhất 2 giờ), khung giờ mở lại, đơn về Mời phỏng vấn để đổi lịch (FR-6.4) |
| Celery `jobmatch.interview_reminders` | Mỗi 15 phút nhắc lịch trong 24 giờ tới cho cả ứng viên và HR, mỗi lịch đúng một lần (FR-6.5) |
| `GET /packages` | Có, yêu cầu đăng nhập theo đặc tả |
| `POST/GET /orders` | Có đơn/QR, thời hạn và quyền sở hữu |
| `POST /webhooks/sepay` | Có khóa webhook, khớp mã/số tiền và idempotence; sai số tiền hoặc đến sau hạn chuyển đơn sang `RECONCILING` (bảng 4.31) |
| `POST /admin/orders/{id}/resolve`, `POST /admin/transactions/{id}/assign` | Admin chấp nhận (PAID + kích hoạt) hoặc từ chối (hủy, đánh dấu cần hoàn) đơn chờ đối soát; gắn giao dịch ghi sai nội dung vào đơn (FR-8.3) |
| `GET /admin/reconcile` | Đối soát nội bộ; khi có `SEPAY_API_TOKEN` lấy thêm lịch sử giao dịch từ API SePay và ghi nhận giao dịch thiếu webhook (BR-18) |
| `POST /reports`, `GET /admin/reports`, `POST /admin/reports/{id}` | Báo cáo vi phạm tin/công ty/người dùng; admin kết luận, có thể đóng tin hoặc khóa tài khoản; người báo cáo nhận thông báo (FR-8.5) |
| `GET /admin/audit-logs?actor_id=` | Lịch sử hoạt động theo người dùng; thao tác vượt quyền được ghi `ACCESS_DENIED` (FR-1.5, FR-1.6) |
| `PATCH /admin/jobs/{id}/moderate` | Có kiểm duyệt tin, chỉ admin |

Frontend đã dùng cùng hợp đồng API. Các đường dẫn trang như `/candidate/...`, `/hr/...` vẫn dùng để điều hướng giao diện, không phải API theo vai trò riêng.

## Quy tắc đã chỉnh trong lần hợp nhất

| Nhóm quy tắc | Hành vi hiện có |
|---|---|
| CV/Job mới hoặc vừa sửa | Vector tính qua worker; revision cũ không ghi đè kết quả mới |
| BR-14–16, BR-26 | Đơn có thời hạn; giao dịch phải đúng mã/số tiền, chưa hết hạn; quyền lợi chỉ kích hoạt khi thanh toán thành công |
| BR-19 | JWT/RBAC và kiểm tra sở hữu ở từng service |
| BR-20 | Gợi ý HR ẩn danh; truy cập CV/file qua phạm vi ứng tuyển vào công ty sở hữu |
| BR-22, BR-25 | Gợi ý dựa trên nội dung trích xuất, yêu cầu Job và bằng chứng; không tự bổ sung thông tin không có |
| BR-23 | Kiểm tra subscription đang active, thời hạn và quyền Premium; mốc thời gian một mình không đủ |
| BR-24 | Điểm thấp hoặc vector chưa sẵn sàng không chặn nộp hồ sơ |
| Chức năng cơ bản ứng viên | Gợi ý việc làm miễn phí; Premium dành cho phân tích chi tiết/đánh giá CV |
| Lịch sử ứng tuyển | Rút/từ chối giữ lịch sử và cho phép nộp đơn mới; một đơn còn hoạt động |

## Phần đã bổ sung theo đặc tả (migration `0003`)

| Hạng mục | Hiện trạng |
|---|---|
| FR-1.1–1.6 tài khoản | Xác minh email, refresh token xoay vòng/thu hồi, đăng xuất phía server, quên/đặt lại mật khẩu, đổi mật khẩu cần mật khẩu cũ, ảnh đại diện, khóa tài khoản thu hồi phiên, nhật ký đăng nhập và thao tác vượt quyền |
| FR-2.4 hồ sơ ứng viên | Bảng `candidate_profiles`, ẩn/hiện hồ sơ khỏi tìm kiếm của HR |
| FR-3.1, 3.3, 3.5 tin tuyển dụng | Trạng thái Nháp, mở lại tin đã đóng, lượt xem và điểm phù hợp trung bình |
| FR-6.4, 6.5 phỏng vấn | Ứng viên hủy/đổi lịch, nhắc lịch tự động qua thông báo và email |
| Bảng 4.31, FR-8.3 đối soát | Trạng thái `RECONCILING`, admin xử lý đơn và gắn giao dịch lạc; giao dịch được duyệt mang trạng thái `RESOLVED`, bị từ chối mang `REFUND_DUE` |
| BR-18 | Đối chiếu với API SePay khi cấu hình token |
| FR-8.5 | Bảng `reports` và trang quản trị Báo cáo vi phạm |
| Bảng 4.9–4.11 | Bảng `skills`, `cv_skills`, `job_skills` đồng bộ trong cùng flush với cột JSON `skills`; migration nạp lại dữ liệu cũ |
| Thông báo email | `app/core/mailer.py` gửi SMTP qua Celery sau commit; chưa cấu hình `SMTP_HOST` thì email được ghi vào log backend/worker |

## Giới hạn còn lại

| Hạng mục | Ghi chú |
|---|---|
| Đánh giá CV toàn diện | Chấm độ đầy đủ bằng quy tắc; chưa đánh giá chất lượng ngôn ngữ bằng LLM (hướng mở rộng) |
| Hoàn tiền | Có quy trình và ledger nội bộ; thao tác chuyển tiền hoàn qua ngân hàng vẫn do admin thực hiện thủ công |
| Đối soát SePay | Ánh xạ trường theo API `userapi/transactions/list` và giả định `id` giao dịch trùng `id` trong webhook; cần xác nhận với tài khoản SePay thật |
| OCR CV | Parser từ chối file scan không đủ văn bản |
| Hồ sơ chi tiết | Học vấn/kinh nghiệm/dự án vẫn lưu trong `cvs.parsed` (JSON), chưa tách bảng riêng |
| Xác nhận môi trường production | Chưa chạy container/pgvector thật, SMTP thật hoặc webhook SePay thật trên máy hiện tại |

Lần hợp nhất này hoàn thiện cấu trúc source, cấu hình chạy và các điều chỉnh nghiệp vụ trực tiếp bị ảnh hưởng bởi kiến trúc. Không ghi nhận các chức năng chưa có là hoàn thành và không tác động database thật của người dùng.
