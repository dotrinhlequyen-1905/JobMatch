// Tạo báo cáo Word: node build_report.js  (cần: npm install docx; chạy make_figures.py trước)
const fs = require('fs')
const path = require('path')
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, ImageRun, PageBreak, TableOfContents, Footer, PageNumber, LevelFormat, BorderStyle, VerticalAlign,
} = require('docx')

const DIMS = JSON.parse(fs.readFileSync(path.join(__dirname, 'image_dims.json'), 'utf8'))
const CONTENT_W = 9071            // A4 21cm - lề trái 3cm - lề phải 2cm (DXA)
const FONT = 'Times New Roman'
let figNo = { ch: 0, n: 0 }, tabNo = { ch: 0, n: 0 }
const body = []

// ------------------------------------------------------------------ helpers
function runs(text, base = {}) {
  // hỗ trợ **đậm** và `mã`
  const out = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0, m
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }))
    const t = m[0]
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }))
    else out.push(new TextRun({ text: t.slice(1, -1), font: 'Consolas', size: 22, ...base }))
    last = m.index + t.length
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }))
  return out
}
const P = (text, opt = {}) => body.push(new Paragraph({ children: runs(text), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 120 }, indent: opt.noIndent ? undefined : { firstLine: 567 }, ...opt.para }))
const B = (text, level = 0) => body.push(new Paragraph({ children: runs(text), numbering: { reference: 'bullets', level },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 } }))
const N = (text) => body.push(new Paragraph({ children: runs(text), numbering: { reference: 'steps', level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 } }))
function chapter(num, title) {
  figNo = { ch: num, n: 0 }; tabNo = { ch: num, n: 0 }
  body.push(new Paragraph({ children: [new PageBreak()] }))
  body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER,
    children: [new TextRun(`CHƯƠNG ${num}. ${title.toUpperCase()}`)] }))
}
const H2 = (t) => body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }))
const H3 = (t) => body.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] }))
function caption(prefix, cnt, text) {
  cnt.n += 1
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
    keepNext: prefix === 'Bảng',   // chú thích bảng (đặt trên bảng) luôn đi cùng bảng
    children: [new TextRun({ text: `${prefix} ${cnt.ch}.${cnt.n}. `, bold: true, italics: true, size: 24 }),
      new TextRun({ text, italics: true, size: 24 })] }))
}
function fig(key, cap, frac = 1, maxH = 820) {
  const [file, w, h] = DIMS[key]
  let W = Math.round(600 * frac), H = Math.round(W * h / w)
  if (H > maxH) { H = maxH; W = Math.round(H * w / h) }
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, keepNext: true,
    children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(__dirname, file)), transformation: { width: W, height: H },
      altText: { title: cap, description: cap, name: key } })] }))
  caption('Hình', figNo, cap)
}
const border = { style: BorderStyle.SINGLE, size: 4, color: '94A3B8' }
const borders = { top: border, bottom: border, left: border, right: border }
function table(headers, rows, fr, cap) {
  const widths = fr.map((f) => Math.round(CONTENT_W * f))
  widths[widths.length - 1] = CONTENT_W - widths.slice(0, -1).reduce((a, b) => a + b, 0)
  const cell = (t, i, head) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: head ? { fill: 'DBE6FE', type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: String(t).split('\n').map((line) => new Paragraph({ children: runs(line, { size: 22, bold: head || undefined }),
      alignment: head ? AlignmentType.CENTER : AlignmentType.LEFT })),
  })
  if (cap) caption('Bảng', tabNo, cap)
  body.push(new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] }))
  body.push(new Paragraph({ spacing: { after: 120 }, children: [] }))
}
function code(lines) {
  for (const [i, l] of lines.entries()) {
    body.push(new Paragraph({ shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
      spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 160 : 0, line: 260 },
      indent: { left: 284, right: 284 }, children: [new TextRun({ text: l || ' ', font: 'Consolas', size: 19 })] }))
  }
}

// ------------------------------------------------------------------ BÌA
const center = (text, size, bold = false, after = 120) => new Paragraph({ alignment: AlignmentType.CENTER,
  spacing: { after }, children: [new TextRun({ text, size, bold })] })
const cover = [
  center('TRƯỜNG ĐẠI HỌC ……………………………', 28, true, 60),
  center('KHOA …………………………………', 28, true, 60),
  center('──────────────', 26, false, 1400),
  center('BÁO CÁO ĐỒ ÁN CHUYÊN NGÀNH', 36, true, 400),
  center('XÂY DỰNG HỆ THỐNG TUYỂN DỤNG THÔNG MINH', 30, true, 60),
  center('HAI CHIỀU TÍCH HỢP AI SO KHỚP CV–JD,', 30, true, 60),
  center('HỖ TRỢ THANH TOÁN TRỰC TUYẾN', 30, true, 60),
  center('VÀ ĐẶT LỊCH PHỎNG VẤN', 30, true, 1400),
  ...[['Học phần', 'Đồ án chuyên ngành'], ['Lớp học phần', 'Đồ án chuyên ngành 1-1-26 (N03)'],
    ['Sinh viên thực hiện', 'Đỗ Trịnh Lệ Quyên'], ['Mã sinh viên', '23010485'], ['Lớp', 'K17-KTPMEL2'],
    ['Giảng viên hướng dẫn', '……………………………']].map(([k, v]) => new Paragraph({
    indent: { left: 2268 }, spacing: { after: 100 },
    children: [new TextRun({ text: `${k}: `, bold: true, size: 26 }), new TextRun({ text: v, size: 26 })] })),
  new Paragraph({ spacing: { before: 1600 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: 'Hà Nội, tháng 9 năm 2026', size: 26, italics: true })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: 'MỤC LỤC', bold: true, size: 30 })] }),
  new TableOfContents('Mục lục', { hyperlink: true, headingStyleRange: '1-3' }),
]

// ================================================================== MỞ ĐẦU
body.push(new Paragraph({ children: [new PageBreak()] }))
body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun('MỞ ĐẦU')] }))
P('Các nền tảng tuyển dụng trực tuyến phổ biến hiện nay (TopCV, VietnamWorks, ITviec, LinkedIn) đã giải quyết tốt nhu cầu đăng tin và tìm việc, nhưng việc lọc hồ sơ chủ yếu vẫn dựa trên **khớp từ khóa**. Cách làm này không hiểu ngữ nghĩa: một CV ghi “ReactJS” có thể bị bỏ sót khi tin tuyển dụng yêu cầu “React”, hay “phát triển mô hình học máy” không được nhận ra là “Machine Learning”. Bên cạnh đó, quy trình tuyển dụng thực tế còn nhiều bài toán vận hành: quản lý vòng đời hồ sơ, tổ chức lịch phỏng vấn khi nhiều người cùng thao tác, thanh toán và đối soát các gói dịch vụ.')
P('Đề tài xây dựng một nền tảng tuyển dụng **hai chiều**: ứng viên nhận gợi ý việc làm phù hợp, nhà tuyển dụng nhận danh sách CV được xếp hạng — cả hai dựa trên một mô hình AI so khớp ngữ nghĩa CV–JD do nhóm tự xây dựng dữ liệu và huấn luyện. Hệ thống đồng thời hiện thực đầy đủ các luồng nghiệp vụ có độ phức tạp kỹ thuật cao: quy trình ứng tuyển theo máy trạng thái, đặt lịch phỏng vấn chống trùng dưới truy cập đồng thời, thanh toán VietQR qua SePay với webhook idempotent, đối soát và hoàn tiền.')
P('Báo cáo gồm 5 chương: Chương 1 giới thiệu tổng quan đề tài; Chương 2 trình bày phân tích và thiết kế hệ thống; Chương 3 trình bày chi tiết phần ứng dụng AI — từ xây dựng dữ liệu, biểu diễn vector, chia tập, huấn luyện đến thiết kế thực nghiệm và kết quả; Chương 4 trình bày cài đặt, giao diện và kiểm thử; Chương 5 là kết luận và hướng phát triển.')

// ================================================================== CHƯƠNG 1
chapter(1, 'Tổng quan đề tài')
H2('1.1. Bối cảnh và vấn đề')
P('Trong lĩnh vực công nghệ thông tin, cùng một kỹ năng thường được viết theo nhiều cách (ReactJS / React.js / React, Golang / Go, Postgres / PostgreSQL), CV và tin tuyển dụng trộn lẫn tiếng Việt và tiếng Anh, và mức độ phù hợp phụ thuộc đồng thời vào vai trò, bộ kỹ năng và số năm kinh nghiệm. Lọc theo từ khóa vì vậy vừa bỏ sót ứng viên tốt, vừa đưa lên các CV chỉ trùng từ ngữ nhưng khác hẳn công việc.')
P('Đề tài giải quyết 6 vấn đề chính theo bản đề xuất:')
B('**So khớp ngữ nghĩa hai chiều:** biểu diễn CV và JD thành vector, xếp hạng và giải thích kết quả (kỹ năng khớp / thiếu) cho cả nhà tuyển dụng lẫn ứng viên.')
B('**Trích xuất thông tin CV:** bóc tách kỹ năng, kinh nghiệm, học vấn từ CV phi cấu trúc (PDF/DOCX) với nhiều bố cục.')
B('**Quy trình ứng tuyển có trạng thái:** chỉ cho phép các chuyển tiếp hợp lệ, ghi lịch sử.')
B('**Đặt lịch phỏng vấn chống trùng:** giữ và giải phóng khung giờ có thời hạn, không để hai ứng viên cùng đặt một khung giờ.')
B('**Thanh toán và đối soát:** VietQR qua SePay, xác nhận tự động bằng webhook, xử lý hết hạn, hoàn tiền, đối soát dòng tiền.')
B('**Bảo mật và phân quyền:** phân quyền theo vai trò (RBAC), bảo vệ dữ liệu CV, đảm bảo tính nhất quán của giao dịch.')
H2('1.2. Mục tiêu và phạm vi')
P('Mục tiêu là xây dựng một hệ thống web chạy được đầy đủ các luồng trên, trong đó phần AI được xây dựng bài bản: tự tạo bộ dữ liệu, có baseline để so sánh, có quy trình đánh giá khách quan và số liệu cụ thể. Hệ thống được thiết kế tổng quát cho nhiều ngành, nhưng phạm vi dữ liệu và đánh giá tập trung vào **ngành CNTT** do kỹ năng dễ chuẩn hóa và nguồn dữ liệu sẵn có. Phiên bản hiện tại chạy trên máy cá nhân (local).')
H2('1.3. Đối tượng sử dụng')
table(['Đối tượng', 'Vai trò / chức năng chính'], [
  ['Ứng viên', 'Quản lý CV (AI trích xuất); nhận gợi ý việc làm bằng AI và phân tích kỹ năng thiếu; ứng tuyển, theo dõi trạng thái, rút đơn; chọn khung giờ phỏng vấn; mua gói Premium.'],
  ['Nhà tuyển dụng (HR)', 'Quản lý hồ sơ công ty, tin tuyển dụng; xem ứng viên được AI xếp hạng (kể cả người chưa ứng tuyển) và mời nộp hồ sơ; xử lý hồ sơ theo quy trình; mở lịch và ghi kết quả phỏng vấn; mua gói đăng tin.'],
  ['Quản trị viên', 'Duyệt công ty và tin; khóa/mở tài khoản; quản lý gói dịch vụ; xem giao dịch, đối soát, duyệt hoàn tiền; thống kê và nhật ký thao tác.'],
  ['Khách', 'Tìm kiếm, xem tin và công ty; đăng ký để ứng tuyển hoặc dùng gợi ý AI.'],
], [0.24, 0.76], 'Đối tượng sử dụng và chức năng chính')
H2('1.4. Công nghệ sử dụng')
table(['Thành phần', 'Công nghệ', 'Lý do lựa chọn'], [
  ['Frontend', 'React 19, TypeScript, Vite, Tailwind CSS, React Router', 'Phổ biến, phát triển nhanh, kiểu dữ liệu chặt chẽ'],
  ['Backend', 'FastAPI (Python), SQLAlchemy 2, Pydantic', 'Cùng ngôn ngữ với phần AI nên model và bộ trích xuất CV chạy trực tiếp trong backend'],
  ['Cơ sở dữ liệu', 'PostgreSQL 17', 'Giao dịch ACID cho đặt lịch và thanh toán; khóa dòng, UPDATE có điều kiện'],
  ['AI', 'sentence-transformers, PyTorch (CUDA), multilingual-e5-base', 'Mô hình embedding đa ngôn ngữ hỗ trợ tiếng Việt, fine-tune được trên GPU 6GB'],
  ['Tác vụ định kỳ', 'APScheduler', 'Giải phóng slot, hết hạn đơn, đóng tin, đối soát mà không cần thêm Redis'],
  ['Thanh toán', 'SePay (webhook) + VietQR', 'Nhận chuyển khoản ngân hàng Việt Nam và báo về hệ thống tự động'],
  ['LLM hỗ trợ dữ liệu', 'OpenRouter: Nemotron-3-Ultra 550B, Nemotron-3-Super 120B', 'Review nhãn và viết lại CV — chỉ dùng khi làm dữ liệu, không dùng lúc chạy web'],
  ['Kiểm thử', 'pytest, Playwright', 'Test luồng nghiệp vụ và test giao diện tự động'],
], [0.17, 0.38, 0.45], 'Công nghệ sử dụng')

// ================================================================== CHƯƠNG 2
chapter(2, 'Phân tích và thiết kế hệ thống')
H2('2.1. Chức năng theo vai trò')
P('Hệ thống có 4 vai trò; các chức năng chính của từng vai trò được tóm tắt ở Hình 2.1. Mọi API đều kiểm tra vai trò ở phía máy chủ (không chỉ ẩn nút trên giao diện).')
fig('fig_usecases', 'Chức năng chính theo vai trò', 1)
H2('2.2. Kiến trúc tổng thể')
P('Hệ thống gồm ba lớp: giao diện React chạy trên trình duyệt, backend FastAPI và cơ sở dữ liệu PostgreSQL (Hình 2.2). Backend là **một tiến trình** chứa cả các API nghiệp vụ lẫn module AI: khi khởi động, backend nạp mô hình embedding lên GPU một lần và nạp toàn bộ vector của tin tuyển dụng và CV vào một **chỉ mục trong bộ nhớ** để tìm kiếm nhanh. Các tác vụ định kỳ (giải phóng khung giờ giữ quá hạn, hủy đơn thanh toán quá hạn, đóng tin hết hạn, đối soát hằng ngày) chạy trong cùng tiến trình bằng APScheduler.')
P('SePay đóng vai trò cầu nối với ngân hàng: người dùng quét mã VietQR và chuyển khoản; khi tiền về, SePay gọi **webhook** của hệ thống kèm nội dung chuyển khoản, hệ thống đối chiếu mã đơn và kích hoạt gói dịch vụ.')
fig('fig_architecture', 'Kiến trúc tổng thể hệ thống', 1)
P('Lựa chọn kiến trúc một tiến trình (thay vì tách AI service, dùng Redis/pgvector) giúp hệ thống chạy được trên máy cá nhân, dễ triển khai và vẫn đáp ứng tốt với quy mô ~8.000 CV và tin: tìm kiếm cosine trên ma trận numpy mất vài mili-giây. Khi mở rộng, có thể tách module AI thành dịch vụ riêng và chuyển chỉ mục sang pgvector mà không đổi giao diện API.')
H2('2.3. Thiết kế cơ sở dữ liệu')
P('Cơ sở dữ liệu gồm 14 bảng; Hình 2.3 thể hiện các bảng và quan hệ chính. Một số ràng buộc được đặt ngay ở tầng CSDL để đảm bảo đúng đắn kể cả khi có lỗi ở tầng ứng dụng:')
B('`applications`: **UNIQUE(job_id, candidate_id)** — một ứng viên chỉ nộp một lần cho mỗi tin.')
B('`interview_slots`: chỉ mục duy nhất có điều kiện trên `application_id` khi trạng thái là HELD/BOOKED — mỗi đơn chỉ giữ/đặt tối đa một khung giờ.')
B('`payment_transactions`: **UNIQUE(sepay_tx_id)** — khóa idempotent cho webhook; `orders.order_code` duy nhất.')
B('Vector embedding của tin và CV lưu trực tiếp trong bảng (kiểu bytea, 768 số thực 32-bit).')
fig('fig_erd', 'Sơ đồ quan hệ các bảng chính', 1)
H2('2.4. Quy trình ứng tuyển — máy trạng thái')
P('Mỗi đơn ứng tuyển đi qua các trạng thái ở Hình 2.4. Các chuyển tiếp hợp lệ được khai báo tĩnh trong một bảng `TRANSITIONS[từ][đến] = {vai trò được phép}`; mọi thao tác đổi trạng thái đều đi qua một hàm duy nhất. Hàm này kiểm tra chuyển tiếp có hợp lệ và vai trò có được phép không, sau đó cập nhật bằng câu lệnh có điều kiện `UPDATE … WHERE id = ? AND status = <trạng thái cũ>`: nếu hai người cùng thao tác, chỉ một câu lệnh cập nhật được dòng, người còn lại nhận thông báo “đơn vừa được cập nhật”. Mỗi lần chuyển đều ghi `application_history` và gửi thông báo cho ứng viên.')
fig('fig_app_state', 'Máy trạng thái đơn ứng tuyển', 1)
table(['Từ trạng thái', 'Có thể chuyển sang', 'Ai được thực hiện'], [
  ['NEW', 'SCREENING, REJECTED / WITHDRAWN', 'HR / Ứng viên'],
  ['SCREENING', 'INTERVIEW_INVITED, REJECTED / WITHDRAWN', 'HR / Ứng viên'],
  ['INTERVIEW_INVITED', 'INTERVIEW_SCHEDULED (xác nhận slot), REJECTED / WITHDRAWN', 'Ứng viên, HR / Ứng viên'],
  ['INTERVIEW_SCHEDULED', 'INTERVIEWED (ghi kết quả), INTERVIEW_INVITED (hủy lịch), REJECTED / WITHDRAWN', 'HR / Ứng viên'],
  ['INTERVIEWED', 'OFFERED, REJECTED', 'HR'],
  ['OFFERED, REJECTED, WITHDRAWN', '— (trạng thái kết thúc)', '—'],
], [0.25, 0.5, 0.25], 'Bảng chuyển trạng thái đơn ứng tuyển')
H2('2.5. Đặt lịch phỏng vấn chống trùng')
P('HR mở các khung giờ (slot) cho một tin; hệ thống chặn tạo khung giờ chồng lên lịch khác của chính HR đó. Ứng viên được mời phỏng vấn chọn một slot: slot chuyển sang **HELD** trong 10 phút; ứng viên phải xác nhận trong thời gian này để slot thành **BOOKED**, nếu không, tác vụ định kỳ trả slot về **OPEN** (Hình 2.5).')
P('Điểm mấu chốt là bước giữ chỗ được thực hiện bằng **một câu lệnh UPDATE nguyên tử** có điều kiện “slot đang trống hoặc đã hết hạn giữ”. Khi hai ứng viên bấm cùng lúc, cơ sở dữ liệu xếp hai câu lệnh nối tiếp nhau; câu thứ hai không còn thỏa điều kiện nên không cập nhật dòng nào và ứng viên đó nhận lỗi 409 “khung giờ vừa được người khác chọn”. Cách này không cần khóa ứng dụng hay Redis. Kiểm thử tự động cho 2 luồng bấm đồng thời vào cùng một slot, lặp lại 10 lần — mọi lần đều đúng một người thành công.')
fig('fig_slot_flow', 'Trạng thái khung giờ phỏng vấn và câu lệnh giữ chỗ nguyên tử', 1)
H2('2.6. Thanh toán VietQR qua SePay và đối soát')
P('Luồng thanh toán được mô tả ở Hình 2.6. Khi người dùng chọn gói, hệ thống tạo đơn trạng thái PENDING (hạn 15 phút) với mã đơn dạng `QTD000123` và trả về ảnh VietQR có sẵn số tiền và nội dung chuyển khoản là mã đơn. Trang thanh toán tự hỏi lại trạng thái mỗi 3 giây.')
fig('fig_payment_flow', 'Luồng thanh toán VietQR – SePay', 1)
P('Webhook là điểm dễ sai nhất vì SePay có thể gửi lặp lại cùng một giao dịch. Hệ thống xử lý **idempotent**: mỗi giao dịch được ghi vào `payment_transactions` với khóa duy nhất `sepay_tx_id` — lần gửi lặp vi phạm ràng buộc và được bỏ qua an toàn. Việc chuyển đơn sang PAID dùng `UPDATE … WHERE status = \'PENDING\'` nên kể cả khi hai webhook khác nhau cùng đến, gói dịch vụ chỉ được kích hoạt một lần. Các tình huống bất thường được phân loại để đối soát:')
table(['Tình huống', 'Cách xử lý'], [
  ['Webhook gửi trùng', 'Bỏ qua (DUPLICATE), không kích hoạt lần hai'],
  ['Chuyển sai số tiền', 'Ghi AMOUNT_MISMATCH, đơn giữ nguyên PENDING'],
  ['Nội dung không có mã đơn', 'Ghi UNMATCHED để quản trị viên xử lý'],
  ['Tiền về sau khi đơn hết hạn / đã thanh toán', 'Ghi LATE — cần hoàn tiền thủ công'],
  ['Đơn PENDING quá hạn', 'Tác vụ định kỳ chuyển EXPIRED'],
  ['Hoàn tiền', 'Chỉ khi đã thanh toán, trong 7 ngày và gói đăng tin chưa dùng; admin duyệt → REFUNDED, thu hồi gói'],
], [0.4, 0.6], 'Các tình huống thanh toán và cách xử lý')
P('Đối soát chạy tự động lúc 0h hằng ngày và có thể chạy tay: kiểm tra mỗi đơn đã thanh toán có đúng một giao dịch khớp cùng số tiền, liệt kê giao dịch lạc/sai tiền và đơn treo. Khi chưa có tài khoản SePay, hệ thống cung cấp nút “giả lập chuyển khoản” — nút này gọi **đúng hàm xử lý webhook thật**, nên luồng được kiểm tra đầy đủ.')
H2('2.7. Gói dịch vụ, bảo mật và phân quyền')
B('**Gói dịch vụ:** HR được đăng miễn phí 2 tin, sau đó cần gói đăng tin; việc trừ lượt dùng `SELECT … FOR UPDATE` để không bị trừ sai khi đăng đồng thời. Ứng viên Premium xem đủ danh sách gợi ý và điểm thành phần chi tiết.')
B('**Xác thực:** JWT (HS256), mật khẩu băm bcrypt; tài khoản bị khóa không đăng nhập được.')
B('**Phân quyền:** mỗi API gắn dependency kiểm tra vai trò; HR chỉ thao tác trên tin của công ty mình; file CV gốc chỉ tải được bởi chủ CV, admin hoặc HR của tin mà ứng viên đã nộp.')
B('**Kiểm duyệt:** công ty và tin tuyển dụng phải được admin duyệt mới hiển thị; sửa nội dung tin sẽ phải duyệt lại.')
B('**Nhật ký:** các thao tác quan trọng (thanh toán, duyệt, chuyển trạng thái, mời ứng tuyển…) được ghi vào `audit_logs`.')

// ================================================================== CHƯƠNG 3
chapter(3, 'Ứng dụng AI so khớp CV–JD')
H2('3.1. Bài toán và hướng tiếp cận')
P('Bài toán: với mỗi tin tuyển dụng (JD), xếp hạng các CV trong kho theo mức độ phù hợp; và ngược lại, với mỗi CV, xếp hạng các tin phù hợp. Kết quả phải **giải thích được** — nhà tuyển dụng cần biết vì sao một CV được xếp cao, ứng viên cần biết mình thiếu kỹ năng gì.')
P('Hướng tiếp cận gồm hai tầng. Tầng thứ nhất là một mô hình **embedding** (bi-encoder): CV và JD được mã hóa độc lập thành vector sao cho cặp phù hợp có vector gần nhau; nhờ mã hóa độc lập, vector của mọi CV/JD được tính trước một lần và tìm kiếm chỉ còn là phép nhân ma trận. Mô hình gốc là `multilingual-e5-base` (đa ngôn ngữ, có tiếng Việt), được **fine-tune trên dữ liệu tự xây dựng**. Tầng thứ hai kết hợp điểm ngữ nghĩa với độ phủ kỹ năng và mức đáp ứng kinh nghiệm để xếp hạng lại và sinh phần giải thích. Toàn bộ quy trình được tóm tắt ở Hình 3.1.')
fig('fig_ai_pipeline', 'Quy trình xây dựng dữ liệu, huấn luyện, đánh giá và triển khai phần AI', 1)

H2('3.2. Xây dựng dữ liệu')
H3('3.2.1. Nguồn dữ liệu tin tuyển dụng và làm sạch')
P('Nguồn JD là bộ dữ liệu công khai **IT-Job-Posting** gồm 3.101 tin tuyển dụng IT thật thu thập từ LinkedIn, ITviec và TopCV (chỉ dùng cho mục đích học tập), mỗi tin có chức danh, công ty, mô tả, địa điểm và danh sách công nghệ. Dữ liệu được làm sạch qua các bước ở Bảng 3.1.')
table(['Bước', 'Mô tả', 'Còn lại'], [
  ['Dữ liệu gốc', '—', '3.101 tin'],
  ['Bỏ trùng, bỏ tin quá ngắn', 'Trùng mô tả hoặc trùng (chức danh, công ty); mô tả < 300 ký tự', '2.510 tin'],
  ['Chuẩn hóa kỹ năng', 'Gộp biến thể về tên chuẩn; bỏ nhãn rỗng/quá chung; chỉ giữ kỹ năng xuất hiện ≥ 3 lần; giữ tin có ≥ 3 kỹ năng hợp lệ', '2.020 tin'],
  ['Chuẩn hóa nhóm nghề', '329 kiểu vai trò → 16 nhóm; bỏ tin không thuộc IT', '**1.978 tin**'],
], [0.25, 0.57, 0.18], 'Các bước làm sạch dữ liệu JD')
P('Kết quả: **1.978 JD**, **16 nhóm nghề**, **384 kỹ năng chuẩn hóa**, trung bình 7,4 kỹ năng/tin; 38% tin viết bằng tiếng Việt, 62% tiếng Anh. Phân bố dữ liệu ở Hình 3.2 — lệch nhiều về Backend, Software Engineer, Full-stack, Frontend, phản ánh đúng thị trường IT.')
fig('fig_data_stats', 'Phân bố JD theo nhóm nghề và các kỹ năng phổ biến', 1)
H3('3.2.2. Chuẩn hóa kỹ năng, nhóm nghề và cấp bậc')
P('Đây là bước quan trọng vì cùng một bộ quy tắc được dùng cho cả dữ liệu huấn luyện lẫn lúc hệ thống chạy thật (trích xuất CV người dùng tải lên, trích kỹ năng từ tin HR đăng). Ba thành phần chính:')
B('**Từ điển kỹ năng:** mỗi tên được đưa về khóa (viết thường, bỏ ký tự đặc biệt trừ + và #), sau đó tra bảng đồng nghĩa. Ví dụ: `ReactJS`, `React.js` → **React**; `Golang` → **Go**; `Postgres` → **PostgreSQL**; `K8s` → **Kubernetes**; `MSSQL` → **SQL Server**; `học máy`, `ML` → **Machine Learning**.')
B('**Nhóm nghề:** 16 luật biểu thức chính quy theo thứ tự ưu tiên trên loại vai trò và chức danh (QA/Tester, DevOps/Cloud, Bảo mật, AI/ML, Data, BA, PM, Mobile, Game, Nhúng, Blockchain, Full-stack, Frontend, Backend, Software Engineer).')
B('**Cấp bậc và số năm kinh nghiệm:** lấy từ chức danh (Intern, Fresher, Junior, Middle, Senior, Lead — khi ghi khoảng như “[Middle, Senior]” thì lấy mức thấp nhất) và từ mô tả bằng biểu thức như “ít nhất 3 năm kinh nghiệm”, “2+ years of experience”.')
H3('3.2.3. Sinh CV tổng hợp có nhãn')
P('Không có bộ CV tiếng Việt công khai kèm nhãn phù hợp với JD, nên CV được **sinh có kiểm soát bằng template**. Với mỗi JD, sinh 3 CV với mức phù hợp biết trước (Bảng 3.2). Vì nhãn suy ra trực tiếp từ cách sinh, nhãn chính xác và có thể tái lập (cố định seed).')
table(['Loại CV', 'Cách sinh', 'Độ phủ kỹ năng JD (TB)', 'Nhãn', 'Số lượng'], [
  ['Phù hợp (fit)', 'Cùng nhóm nghề, có 80–100% kỹ năng JD, đủ số năm kinh nghiệm', '0,97', '2', '1.978'],
  ['Thiếu kỹ năng (partial_skill)', 'Cùng nhóm nghề, có 40–66% kỹ năng JD', '0,49', '1', '1.454'],
  ['Thiếu kinh nghiệm (partial_senior)', 'Đủ kỹ năng nhưng thiếu 2–3 năm so với yêu cầu', '0,94', '1', '524'],
  ['Không phù hợp khó (hard_neg)', 'Nhóm nghề khác hẳn, chỉ trùng vài kỹ năng chung (Git, Docker…)', '0,13', '0', '1.978'],
], [0.24, 0.4, 0.14, 0.08, 0.14], 'Ba loại CV được sinh cho mỗi JD')
P('Để CV không bị lặp khuôn và dạy mô hình hiểu biến thể, bộ sinh áp dụng: viết kỹ năng theo nhiều biến thể (ReactJS / React.js); khoảng 20% kỹ năng chỉ xuất hiện trong phần mô tả kinh nghiệm chứ không liệt kê ở mục kỹ năng (giống CV thật); 55% CV tiếng Việt, 45% tiếng Anh; xáo trộn thứ tự các mục; câu mô tả công việc đặc thù chỉ ghép với kỹ năng tiêu biểu của nhóm nghề đó (tránh câu vô nghĩa như “vẽ wireframe bằng Java”). Tổng cộng **5.934 CV**, trung bình ~190 từ/CV. Ngoài ra 200 CV thuộc tập test được xuất ra file PDF (2 bố cục) và DOCX kèm đáp án để đánh giá bộ trích xuất.')
H3('3.2.4. Tăng cường dữ liệu bằng LLM')
P('Dữ liệu sinh bằng template có hai hạn chế: câu văn còn lặp, và nhãn do luật suy ra có thể sai trong vài trường hợp. Đề tài dùng LLM (qua OpenRouter, các model miễn phí) để khắc phục cả hai. Trước tiên, 9 model được thử trên cùng hai tác vụ mẫu:')
table(['Model', 'Sinh / viết lại CV', 'Chấm nhãn', 'Kết luận'], [
  ['Nemotron-3-Super 120B', 'Tốt: đủ kỹ năng, không bịa thêm', 'Lỏng, thiếu nhất quán', '**Dùng để viết lại CV**'],
  ['Nemotron-3-Ultra 550B', 'Hết token do suy luận quá dài', 'Tốt nhất, lý do chính xác', '**Dùng để chấm nhãn**'],
  ['dots-3-note', 'Nhanh nhưng bịa thêm kỹ năng', 'Khá', 'Dự phòng khi Ultra quá tải'],
  ['Nemotron-3.5-Lightning', 'Hết token', 'Hết token', 'Loại'],
  ['Qwen-3.8-27B, Gemma-4 (×2)', 'Thường bị giới hạn tốc độ', '—', 'Dự phòng'],
  ['Inkling (×2)', 'Bị chặn truy cập', '—', 'Loại'],
], [0.26, 0.28, 0.22, 0.24], 'So sánh các LLM miễn phí cho hai tác vụ làm dữ liệu')
P('**Review nhãn:** LLM chấm lại **5.252 cặp** JD–CV (toàn bộ cặp train và 500 cặp dành cho gán nhãn tay) theo thang 0/1/2, kèm kỹ năng khớp/thiếu và lý do. Các cặp được gộp theo JD (mỗi JD chỉ gửi một lần kèm các CV của nó) và gửi 24 cặp/lần để tiết kiệm lượt gọi. LLM đồng ý với nhãn luật **91,4%** trên cặp train và **84,4%** trên 500 cặp gán nhãn tay; gần như không có cặp bị đảo ngược hẳn (Hình 3.3). Chính LLM đã phát hiện lỗi của bộ sinh (kỹ năng ghép vào câu vô nghĩa), giúp sửa bộ sinh từ gốc. **365 bộ ba train** (11,5%) mà LLM cho là nhãn sai được loại ra, tạo thành tập train “sạch”.')
fig('fig_agreement', 'Ma trận đồng thuận giữa nhãn luật và nhãn LLM', 0.85)
P('**Viết lại CV:** LLM viết lại CV của tập test cho tự nhiên như CV người thật viết, với ràng buộc giữ nguyên họ tên, công ty, thời gian, trường và **chỉ dùng đúng danh sách kỹ năng**. Mỗi bản viết lại được kiểm tra tự động: đủ mọi kỹ năng (tính cả biến thể), không thêm công nghệ ngoài danh sách (cho phép tối đa 2 kỹ năng chung như Git, SQL), đúng tên, đúng ngôn ngữ; bản không đạt bị loại (mỗi CV thử tối đa 2 lần). Kết quả có **281 CV** tập test đạt yêu cầu, tạo thành tập đánh giá `test_llm` gần với CV thật hơn.')

H2('3.3. Chia tập huấn luyện, kiểm định và kiểm tra')
P('Dữ liệu được chia **theo JD** với tỉ lệ 80/10/10, phân tầng theo 16 nhóm nghề để tập nào cũng có đủ các nhóm (Hình 3.4). Mọi CV sinh cho một JD đi cùng tập với JD đó. Nếu chia ngẫu nhiên theo cặp, cùng một JD có thể vừa xuất hiện khi train vừa khi test, khiến kết quả tốt giả tạo.')
fig('fig_split', 'Cách chia dữ liệu theo JD', 1)
P('Với tập val và test, thay vì chỉ dùng 3 nhãn gốc của mỗi JD, đề tài **chấm lại toàn bộ ma trận JD × CV** (197 × 591 cặp mỗi tập) bằng cùng một luật. Lý do: một CV sinh cho JD A hoàn toàn có thể phù hợp với JD B cùng nhóm nghề; nếu coi là “không phù hợp” thì mô hình bị phạt oan. Luật chấm mức liên quan:')
table(['Mức', 'Điều kiện'], [
  ['2 — phù hợp', 'Cùng nhóm nghề, có ≥ 70% kỹ năng JD và số năm kinh nghiệm ≥ yêu cầu − 1'],
  ['1 — phù hợp một phần', 'Cùng nhóm nghề và có ≥ 40% kỹ năng JD, hoặc nhóm nghề liên quan (vd Backend – Full-stack) và có ≥ 60%'],
  ['0 — không phù hợp', 'Các trường hợp còn lại'],
], [0.25, 0.75], 'Luật chấm mức liên quan cho tập val/test')
P('Luật này khớp 97,3% với nhãn gốc lúc sinh. Mỗi JD trong tập test có trung bình ~20 CV liên quan (khoảng 2–3 CV mức 2). Tập **val** dùng để chọn checkpoint tốt nhất trong lúc huấn luyện và dò trọng số điểm tổng hợp; tập **test** chỉ dùng để báo cáo kết quả cuối cùng.')

H2('3.4. Biểu diễn văn bản và so khớp vector')
H3('3.4.1. Từ CV/JD đến vector')
P('Quy trình biến đổi được mô tả ở Hình 3.5. CV người dùng tải lên được đọc (PDF bằng PyMuPDF, DOCX bằng python-docx), tách thành các mục (mục tiêu, kỹ năng, kinh nghiệm, dự án, học vấn…), rồi trích ra kỹ năng (dò từ điển, bắt biến thể), số năm kinh nghiệm (gộp các khoảng thời gian làm việc, khoảng chồng nhau chỉ tính một lần), danh sách vị trí đã làm và ngành học. Tin tuyển dụng đã có sẵn các trường chuẩn hóa.')
P('Thay vì đưa toàn văn CV (thường dài hơn giới hạn độ dài của mô hình, nhiều nhiễu như thông tin liên hệ) vào mô hình, hệ thống tạo một **văn bản “profile” chuẩn hóa ngắn**. Ví dụ:')
code(['JD: Vị trí: Java Backend Developer. Nhóm: Lập trình viên Backend. Cấp bậc: Middle, yêu cầu tối thiểu',
  '    2 năm kinh nghiệm. Kỹ năng yêu cầu: Java, Spring Boot, PostgreSQL, Docker, Kafka.',
  'CV: Ứng viên: Senior Backend Developer. Cấp bậc: Senior, 4 năm kinh nghiệm. Kỹ năng: Java, Spring Boot,',
  '    PostgreSQL, Redis, Docker. Kinh nghiệm: Senior Backend Developer (2023-nay); Junior Backend',
  '    Developer (2022-2023). Học vấn: Công nghệ thông tin.'])
P('Đúng một hàm tạo profile được dùng cho cả dữ liệu huấn luyện và lúc hệ thống chạy thật (kiểm tra: 5.934/5.934 CV và 1.978/1.978 JD cho ra văn bản giống hệt từng ký tự). Điều này quan trọng: nếu định dạng lúc chạy khác lúc train, mô hình đã fine-tune sẽ hoạt động kém đi. Văn bản được thêm tiền tố `query: ` theo quy ước của họ mô hình e5, rồi mã hóa thành **vector 768 chiều, chuẩn hóa độ dài bằng 1**.')
fig('fig_matching', 'Biểu diễn CV/JD thành vector và cách tính điểm phù hợp', 1)
H3('3.4.2. So sánh vector và xếp hạng')
P('Do vector đã chuẩn hóa, độ tương đồng **cosine** giữa CV và JD chính là **tích vô hướng** của hai vector. Toàn bộ vector được giữ trong một ma trận numpy; để tìm CV cho một JD chỉ cần một phép nhân ma trận–vector rồi sắp xếp. Việc xếp hạng gồm hai bước:')
N('**Lọc nhanh:** lấy 200 CV (hoặc tin) có cosine cao nhất.')
N('**Xếp hạng lại** 200 kết quả này bằng điểm tổng hợp: `điểm = 0,4 × ngữ nghĩa + 0,5 × độ phủ kỹ năng + 0,1 × kinh nghiệm`, trong đó ngữ nghĩa là cosine đã đưa về thang 0–1, độ phủ kỹ năng = số kỹ năng JD mà CV có / số kỹ năng JD yêu cầu, kinh nghiệm = min(1, số năm của CV / số năm yêu cầu). Bộ trọng số được **dò trên tập val** (lưới tìm kiếm), không dùng tập test.')
P('Phần giải thích (gap analysis) được suy ra trực tiếp: **kỹ năng khớp** = JD ∩ CV, **kỹ năng thiếu** = JD − CV, **kỹ năng khác** = CV − JD, cùng ba điểm thành phần. Chiều ngược lại (gợi ý việc làm cho ứng viên) dùng đúng cơ chế này với vai trò CV và JD đổi chỗ. Khi CV mới được tải lên hoặc tin được duyệt, vector được tính và thêm ngay vào chỉ mục.')

H2('3.5. Huấn luyện mô hình')
P('Mô hình được fine-tune với hàm mất mát **Multiple Negatives Ranking**: mỗi mẫu là bộ ba (JD, CV phù hợp, CV không/ít phù hợp); trong một batch, mô hình phải xếp CV phù hợp của mỗi JD cao hơn CV “khó” của nó **và** cao hơn mọi CV của các JD khác trong batch — nhờ vậy một batch 64 JD cho ra hàng nghìn cặp so sánh. Phiên bản “cached” của hàm mất mát cho phép dùng batch lớn trên GPU 6GB bằng cách tính gradient theo từng khối nhỏ.')
table(['Tham số', 'Giá trị'], [
  ['Mô hình gốc', 'intfloat/multilingual-e5-base (vector 768 chiều)'],
  ['Dữ liệu', '3.168 bộ ba (gốc) hoặc 2.803 bộ ba (đã lọc bằng LLM)'],
  ['Batch / khối nhỏ', '64 JD mỗi bước / 16 (toàn văn: 8)'],
  ['Tốc độ học, số epoch', '2e-5, warmup 10%, 3 epoch'],
  ['Độ dài tối đa', '256 token (profile), 384 token (toàn văn)'],
  ['Độ chính xác số', 'fp16 trên GPU RTX 4050 Laptop 6GB'],
  ['Chọn mô hình', 'Đánh giá NDCG@10 trên val mỗi 25 bước, giữ checkpoint tốt nhất'],
], [0.3, 0.7], 'Cấu hình huấn luyện')
P('Ba cấu hình được huấn luyện để so sánh ảnh hưởng của dữ liệu và dạng văn bản (Hình 3.6). Dữ liệu đã lọc bằng LLM tuy ít hơn 11,5% nhưng cho kết quả tốt hơn; dạng “profile” tốt hơn hẳn toàn văn. Cấu hình B (profile, dữ liệu sạch) được chọn đưa vào hệ thống; thời gian huấn luyện chỉ khoảng 4 phút.')
fig('fig_training', 'NDCG@10 trên tập val trước và sau fine-tune của 3 cấu hình', 0.8)

H2('3.6. Thiết kế thực nghiệm')
H3('3.6.1. Các phương pháp so sánh')
table(['Phương pháp', 'Mô tả'], [
  ['BM25', 'Xếp hạng theo từ khóa truyền thống — đại diện cho cách lọc của các nền tảng hiện có'],
  ['Chỉ kỹ năng', 'Chỉ dùng độ phủ kỹ năng sau chuẩn hóa (không dùng AI)'],
  ['e5 gốc', 'Mô hình multilingual-e5-base chưa fine-tune, chỉ dùng cosine'],
  ['e5 fine-tune', 'Mô hình sau fine-tune (cấu hình B), chỉ dùng cosine'],
  ['… + hybrid', 'Điểm tổng hợp ngữ nghĩa + kỹ năng + kinh nghiệm, trọng số dò trên val cho từng mô hình'],
], [0.22, 0.78], 'Các phương pháp được so sánh')
H3('3.6.2. Chỉ số đánh giá')
B('**NDCG@10** (chỉ số chính): đánh giá chất lượng 10 kết quả đầu, có tính mức liên quan (2 quan trọng hơn 1) và vị trí (đúng ở hạng 1 có giá trị hơn ở hạng 10). Bằng 1 khi thứ tự hoàn hảo.')
B('**MRR@10:** nghịch đảo thứ hạng của CV phù hợp (mức 2) đầu tiên — đo việc “người phù hợp nhất có được đưa lên đầu không”.')
B('**Recall@20, Recall@50:** tỉ lệ CV phù hợp nằm trong top 20/50 — quan trọng cho bước lọc nhanh.')
B('**P@3 và độ chính xác cặp** (dùng cho nhãn LLM): tỉ lệ kết quả liên quan trong top 3; tỉ lệ cặp CV khác nhãn được xếp đúng thứ tự.')
H3('3.6.3. Bốn bối cảnh đánh giá')
P('Vì CV huấn luyện là dữ liệu tổng hợp, chỉ đánh giá trên một tập là chưa đủ tin cậy. Đề tài đánh giá trong 4 bối cảnh, mỗi bối cảnh trả lời một câu hỏi:')
table(['Bối cảnh', 'Dữ liệu', 'Câu hỏi trả lời'], [
  ['Test', '197 JD × 591 CV template, nhãn luật', 'Mô hình có học được bài toán không?'],
  ['Đầu-cuối trên CV do LLM viết', '188 JD × 281 CV viết tự nhiên; CV đi qua bộ trích xuất như hệ thống thật', 'Có hoạt động với CV không theo template, kể cả sai số của bước trích xuất?'],
  ['Nhãn do LLM chấm', '50 JD × 10 CV, nhãn độc lập với luật kỹ năng', 'Kết quả có phụ thuộc vào cách tạo nhãn không?'],
  ['Trích xuất CV', '200 file PDF/DOCX có đáp án', 'Bộ đọc CV chính xác đến đâu?'],
], [0.22, 0.4, 0.38], 'Các bối cảnh đánh giá')

H2('3.7. Kết quả')
H3('3.7.1. Xếp hạng CV cho tin tuyển dụng')
table(['Phương pháp', 'NDCG@10', 'MRR@10', 'Recall@20', 'Recall@50', 'CV→JD NDCG@10'], [
  ['BM25', '0,686', '0,742', '0,892', '0,941', '0,581'],
  ['Chỉ kỹ năng', '0,856', '0,949', '0,990', '0,999', '0,813'],
  ['e5 gốc', '0,630', '0,665', '0,871', '0,957', '0,636'],
  ['**e5 fine-tune**', '**0,842**', '0,906', '0,973', '**0,999**', '**0,845**'],
  ['e5 gốc + hybrid', '0,917', '0,984', '0,995', '1,000', '—'],
  ['e5 fine-tune + hybrid', '0,905', '0,987', '0,995', '1,000', '—'],
], [0.26, 0.13, 0.13, 0.14, 0.14, 0.2], 'Kết quả trên tập test (197 JD × 591 CV)')
table(['Phương pháp', 'NDCG@10', 'MRR@10', 'Recall@20', 'Recall@50'], [
  ['BM25 (toàn văn CV)', '0,504', '0,390', '0,728', '0,857'],
  ['Chỉ kỹ năng', '0,791', '0,612', '0,937', '0,991'],
  ['e5 gốc', '0,596', '0,421', '0,852', '0,950'],
  ['**e5 fine-tune**', '**0,808**', '0,590', '0,935', '0,981'],
  ['e5 gốc + hybrid', '0,861', '0,640', '0,958', '0,992'],
  ['e5 fine-tune + hybrid', '0,849', '0,641', '0,960', '0,992'],
], [0.32, 0.17, 0.17, 0.17, 0.17], 'Kết quả đầu-cuối trên CV do LLM viết lại (188 JD × 281 CV)')
table(['Phương pháp', 'NDCG@10', 'P@3', 'Độ chính xác cặp'], [
  ['BM25', '0,921', '0,840', '0,913'],
  ['Chỉ kỹ năng', '0,979', '0,880', '0,940'],
  ['e5 gốc', '0,922', '0,847', '0,921'],
  ['**e5 fine-tune**', '**0,972**', '0,873', '**0,958**'],
  ['e5 gốc + hybrid', '0,984', '0,907', '0,967'],
  ['e5 fine-tune + hybrid', '0,984', '0,893', '0,951'],
], [0.34, 0.22, 0.22, 0.22], 'Kết quả trên nhãn do LLM chấm (50 JD × 10 CV)')
fig('fig_results', 'So sánh NDCG@10 của các phương pháp trong ba bối cảnh', 1)
P('**Nhận xét:**')
B('**Fine-tune cải thiện rõ rệt phần AI** ở cả ba bối cảnh: NDCG@10 tăng từ 0,630 lên 0,842 (+34%) trên test, từ 0,596 lên 0,808 (+36%) khi chạy đầu-cuối trên CV viết tự nhiên, và từ 0,922 lên 0,972 trên nhãn LLM. Mô hình gốc khi chưa fine-tune còn **kém hơn BM25** trên tập test — cho thấy mô hình đa ngôn ngữ tổng quát chưa phân biệt tốt các cặp CV–JD cùng ngành IT (mọi cặp đều có cosine cao); fine-tune dạy mô hình tách bạch các nhóm nghề.')
B('**Kết quả giữ vững trên CV không theo template:** chênh lệch giữa tập test template (0,842) và đầu-cuối trên CV do LLM viết (0,808) nhỏ, trong khi BM25 giảm mạnh (0,686 → 0,504) do CV viết tự do dùng từ ngữ đa dạng hơn — đúng điểm yếu của lọc từ khóa mà đề tài đặt ra.')
B('**Về điểm hybrid:** khi đã có thành phần kỹ năng, mô hình gốc và mô hình fine-tune cho kết quả tương đương (chênh lệch ~0,01). Một phần nguyên nhân là nhãn test được tạo từ độ phủ kỹ năng nên thành phần kỹ năng có lợi thế sẵn; đây là hạn chế của dữ liệu tổng hợp. Hệ thống vẫn dùng mô hình fine-tune vì bước **lọc nhanh 200 ứng viên đầu tiên chỉ dùng cosine**, và ở bước này mô hình fine-tune có Recall@50 = 0,999 (so với 0,957), đồng thời phân biệt rõ các cặp khác nghề (ví dụ CV lập trình viên Mobile với tin Node.js Lead chỉ có độ tương đồng ngữ nghĩa ~10%, trong khi mô hình gốc cho ~0,8 với hầu hết cặp IT).')
H3('3.7.2. Trích xuất thông tin CV')
table(['Tập', 'Precision kỹ năng', 'Recall kỹ năng', 'F1', 'Số năm KN đúng', 'Email / SĐT', 'Nhóm nghề'], [
  ['200 file PDF/DOCX', '0,911', '0,995', '0,951', '99%', '100%', '87,5%'],
  ['281 CV do LLM viết', '0,933', '0,987', '0,959', '100%', '—', '—'],
], [0.22, 0.14, 0.13, 0.1, 0.14, 0.13, 0.14], 'Kết quả trích xuất thông tin CV')
P('Ngoài ra, danh sách vị trí đã làm được trích đúng hoàn toàn ở 183/200 file và ngành học ở 189/200 file. Lỗi còn lại chủ yếu là nhận nhầm các từ chung (như “CRM”, “Security”) thành kỹ năng và các dòng bị ngắt trong bố cục hai cột. Lưu ý các file kiểm thử được sinh từ cùng bộ template nên kết quả trên CV thật dự kiến thấp hơn; bộ CV do LLM viết lại cho thấy bộ trích xuất vẫn ổn định với văn phong tự do.')

H2('3.8. Hạn chế')
B('CV huấn luyện là dữ liệu tổng hợp; dù đã có tập CV do LLM viết lại và nhãn LLM độc lập, cần đánh giá thêm trên CV thật và nhãn do người chấm (đã chuẩn bị sẵn file 500 cặp để gán nhãn tay).')
B('Nhãn val/test được tạo từ luật dựa trên kỹ năng, nên các phương pháp dùng kỹ năng có lợi thế khi đánh giá trên các tập này.')
B('Bộ trích xuất dựa trên từ điển 384 kỹ năng IT; kỹ năng mới hoặc ngành khác cần bổ sung từ điển. Chưa hỗ trợ CV dạng ảnh scan (OCR).')
B('Một số nhóm nghề có ít dữ liệu (Data Analyst, Blockchain, BA).')

// ================================================================== CHƯƠNG 4
chapter(4, 'Cài đặt, giao diện và kiểm thử')
H2('4.1. Cấu trúc mã nguồn')
table(['Thư mục', 'Nội dung'], [
  ['data_pipeline/', 'Làm sạch JD, từ điển kỹ năng, sinh CV, chia tập, xuất PDF/DOCX, file gán nhãn tay, gộp kết quả LLM'],
  ['llm/', 'So sánh model LLM, review nhãn và viết lại CV (chạy nền, tự tiếp tục khi bị ngắt)'],
  ['ml/', 'Huấn luyện, dò trọng số hybrid, các kịch bản đánh giá'],
  ['backend/app/', 'FastAPI: routers (API), services (trạng thái, đặt lịch, thanh toán), ai (trích xuất, embedding, so khớp)'],
  ['frontend/src/', 'React: trang công khai, ứng viên, nhà tuyển dụng, quản trị viên'],
  ['backend/tests/, e2e/', 'Kiểm thử luồng nghiệp vụ (pytest) và giao diện (Playwright)'],
  ['models/', 'Mô hình đã fine-tune dùng trong hệ thống'],
], [0.25, 0.75], 'Cấu trúc mã nguồn')
P('Dữ liệu demo gồm 1.978 tin tuyển dụng thật (1.083 công ty), 5.934 ứng viên với CV, các gói dịch vụ và 3 tài khoản demo cho ba vai trò; toàn bộ được nạp bằng một lệnh.')
H2('4.2. Giao diện hệ thống')
P("Các ảnh giao diện JobMatch dưới đây được chụp bằng dữ liệu demo trong môi trường kiểm thử riêng. Phiên chụp dùng embedding hashing và tắt Cross-Encoder để minh họa giao diện; các điểm trên ảnh không phải kết quả E5/Cross-Encoder hoặc số liệu thực nghiệm ở Chương 3. Dữ liệu thanh toán và webhook trên ảnh là dữ liệu giả lập.")
fig('01_home', 'Trang chủ', 0.95)
fig('03_candidate_recommendations', 'Gợi ý việc làm bằng AI cho ứng viên, kèm phân tích kỹ năng', 0.95)
fig('04_candidate_cv_parsed', 'Kết quả trích xuất CV sau khi tải file PDF — ứng viên có thể sửa lại', 0.95)
fig('05_candidate_job_match', 'Chi tiết tin tuyển dụng và mức độ phù hợp với CV của ứng viên', 0.95)
fig('08_hr_ai_candidates', 'Nhà tuyển dụng xem ứng viên được AI xếp hạng và mời ứng tuyển', 0.95)
fig('07_hr_application_detail', 'Xử lý hồ sơ ứng viên theo quy trình', 0.95)
fig('10_candidate_slot_held', 'Ứng viên giữ chỗ khung giờ phỏng vấn (còn 10 phút để xác nhận)', 0.95)
fig('12_checkout_qr', 'Trang thanh toán VietQR', 0.95)
fig('14_admin_dashboard', 'Thống kê của quản trị viên', 0.95)
fig('15_admin_reconcile', 'Đối soát giao dịch', 0.95)
fig('mobile_menu_open', 'Giao diện trên điện thoại', 0.35)
H2('4.3. Kiểm thử')
P('Hệ thống có ba lớp kiểm thử tự động:')
table(['Loại', 'Nội dung', 'Kết quả'], [
  ['Kiểm thử nghiệp vụ (pytest, CSDL riêng)', '14 kịch bản: trích xuất + so khớp; máy trạng thái (nhảy cóc, sai vai trò, trạng thái kết thúc); 2 người giữ cùng slot đồng thời ×10 lần; giữ chỗ hết hạn; webhook trùng / sai tiền / đến muộn; hết hạn đơn; quota và hoàn tiền; phân quyền; mời ứng tuyển; tin hết hạn; giới hạn Premium; kiểm tra dữ liệu gói', '14/14 đạt'],
  ['Kiểm thử giao diện (Playwright)', '16 bước đi hết luồng của khách, ứng viên, HR, admin trên trình duyệt thật; bắt lỗi JavaScript và lỗi máy chủ', 'Đạt, không lỗi'],
  ['Kiểm tra trên điện thoại', '11 trang ở màn 390px, phát hiện tràn ngang', 'Không trang nào tràn'],
], [0.24, 0.6, 0.16], 'Tổng hợp kiểm thử')

// ================================================================== CHƯƠNG 5
chapter(5, 'Kết luận và hướng phát triển')
H2('5.1. Kết quả đạt được')
B('Xây dựng hoàn chỉnh nền tảng tuyển dụng hai chiều, đáp ứng đầy đủ các chức năng trong đề xuất cho 4 vai trò.')
B('Hiện thực các luồng có độ phức tạp kỹ thuật cao và có kiểm thử chứng minh: máy trạng thái ứng tuyển, đặt lịch chống trùng bằng câu lệnh nguyên tử, thanh toán với webhook idempotent, đối soát và hoàn tiền.')
B('Tự xây dựng bộ dữ liệu CV–JD (1.978 JD thật, 5.934 CV có nhãn), dùng LLM để lọc nhãn sai và tạo tập kiểm tra gần với CV thật.')
B('Fine-tune mô hình so khớp ngữ nghĩa trên GPU cá nhân, cải thiện NDCG@10 khoảng 34–36% so với mô hình gốc và vượt lọc từ khóa BM25; đánh giá khách quan trong 4 bối cảnh.')
B('Bộ trích xuất CV đạt F1 kỹ năng ~0,95 trên file PDF/DOCX.')
H2('5.2. Hướng phát triển')
B('Đánh giá trên CV thật và nhãn do người chấm; thu thập phản hồi của nhà tuyển dụng (bấm mời / từ chối) để tiếp tục huấn luyện.')
B('Thêm mô hình xếp hạng lại (cross-encoder) cho top 20 kết quả; mở rộng từ điển kỹ năng sang các ngành khác; hỗ trợ CV dạng ảnh (OCR).')
B('Triển khai lên máy chủ: tách module AI thành dịch vụ riêng, dùng pgvector, Redis và hàng đợi thông báo email.')
B('Gợi ý tương hỗ (reciprocal recommendation), phỏng vấn trực tuyến, đánh giá kỹ năng và phân tích thị trường lao động.')
H2('Tài liệu tham khảo')
for (const r of [
  'Wang L. và cộng sự (2024). Multilingual E5 Text Embeddings: A Technical Report. arXiv:2402.05672.',
  'Reimers N., Gurevych I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP 2019.',
  'Henderson M. và cộng sự (2017). Efficient Natural Language Response Suggestion for Smart Reply (Multiple Negatives Ranking Loss). arXiv:1705.00652.',
  'Gao L. và cộng sự (2021). Scaling Deep Contrastive Learning Batch Size under Memory Limited Setup (GradCache). RepL4NLP 2021.',
  'Robertson S., Zaragoza H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond.',
  'Järvelin K., Kekäläinen J. (2002). Cumulated gain-based evaluation of IR techniques (NDCG). ACM TOIS.',
  'Bộ dữ liệu IT-Job-Posting: github.com/SonPhatTranDeveloper/IT-Job-Posting.',
  'Tài liệu SePay (webhook, VietQR): docs.sepay.vn · FastAPI: fastapi.tiangolo.com · sentence-transformers: sbert.net.',
]) body.push(new Paragraph({ children: runs(r), numbering: { reference: 'refs', level: 0 }, spacing: { after: 80 } }))

// ------------------------------------------------------------------ tài liệu
const doc = new Document({
  creator: 'Đỗ Trịnh Lệ Quyên', title: 'Báo cáo đồ án chuyên ngành — Hệ thống tuyển dụng thông minh',
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 26 }, paragraph: { spacing: { line: 312 } } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, font: FONT, color: '000000' }, paragraph: { spacing: { before: 120, after: 360 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: '000000' }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1, keepNext: true } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, italics: true, font: FONT, color: '000000' }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567, hanging: 284 } } } }] },
    { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567, hanging: 340 } } } }] },
    { reference: 'refs', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '[%1]', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567, hanging: 567 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 },
      margin: { top: 1134, bottom: 1134, left: 1701, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 24 })] })] }) },
    children: [...cover, ...body],
  }],
})
Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, 'BaoCao_DoAnChuyenNganh_JobMatch.docx')
  fs.writeFileSync(out, buf)
  console.log('Đã tạo', out)
})
