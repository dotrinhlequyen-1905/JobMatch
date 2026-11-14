from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = r"D:\doanchuyennganh\Tom_tat_cong_viec_JobMatch.docx"

doc = Document()
section = doc.sections[0]
section.top_margin = Cm(2.2)
section.bottom_margin = Cm(2.0)
section.left_margin = Cm(2.35)
section.right_margin = Cm(2.15)

styles = doc.styles
styles['Normal'].font.name = 'Calibri'
styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), 'Arial')
styles['Normal'].font.size = Pt(11)
styles['Normal'].paragraph_format.space_after = Pt(6)
styles['Normal'].paragraph_format.line_spacing = 1.18
for name, size in [('Title', 19), ('Heading 1', 14), ('Heading 2', 12)]:
    st = styles[name]
    st.font.name = 'Calibri'
    st._element.rPr.rFonts.set(qn('w:eastAsia'), 'Arial')
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.font.bold = True
    st.paragraph_format.space_before = Pt(13 if name != 'Title' else 0)
    st.paragraph_format.space_after = Pt(6)

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tc_pr.append(shd)

def cell_text(cell, text, bold=False, color=None):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(9.5)
    if color:
        r.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def set_cell_margins(cell, top=90, start=100, bottom=90, end=100):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar')
        tcPr.append(tcMar)
    for m, v in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = tcMar.find(qn('w:' + m))
        if node is None:
            node = OxmlElement('w:' + m)
            tcMar.append(node)
        node.set(qn('w:w'), str(v))
        node.set(qn('w:type'), 'dxa')

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        shade(c, '1F4E78')
        cell_text(c, h, True, (255, 255, 255))
        set_cell_margins(c)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, value in enumerate(row):
            if ri % 2 == 1:
                shade(cells[i], 'EAF2F8')
            cell_text(cells[i], value)
            set_cell_margins(cells[i])
    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return t

def para(text='', bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p

def bullet(text, level=0):
    p = doc.add_paragraph(style='List Bullet' if level == 0 else 'List Bullet 2')
    p.add_run(text)
    return p

def heading(text, level=1):
    return doc.add_heading(text, level=level)

# Title block
p = doc.add_paragraph(style='Title')
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run('Tóm tắt công việc và mức độ tham gia dự án JobMatch')
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Đồ án nền tảng tuyển dụng thông minh có hỗ trợ AI')
r.bold = True
r.font.size = Pt(12)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run('Sinh viên thực hiện: Đỗ Trịnh Lệ Quyên').italic = True

para('Bản tóm tắt này trình bày phạm vi công việc tôi đã thực hiện, cách tôi tham gia vào quá trình thiết kế và phát triển hệ thống, các công cụ đã sử dụng, cũng như phần chuyên môn sâu được trao đổi với người có chuyên môn. Tôi chịu trách nhiệm chính về việc xác định bài toán, thiết kế nghiệp vụ, thiết kế trải nghiệm người dùng, định hướng kiến trúc và kiểm tra sự phù hợp giữa yêu cầu với hệ thống triển khai.')

heading('1. Mục tiêu và bài toán giải quyết')
para('Bài toán xuất phát từ khó khăn của ứng viên khi phải lọc nhiều tin tuyển dụng bằng từ khóa và của nhà tuyển dụng khi phải đọc nhiều CV thủ công. Cách tìm kiếm theo từ khóa dễ bỏ sót những trường hợp có cùng năng lực nhưng diễn đạt khác nhau, ví dụ ReactJS và React.js. Giải pháp JobMatch tổ chức toàn bộ quy trình tuyển dụng trong một hệ thống và bổ sung chức năng gợi ý hai chiều giữa CV và tin tuyển dụng.')
bullet('Ứng viên tải CV, nhận gợi ý việc làm, xem kỹ năng phù hợp hoặc còn thiếu, ứng tuyển và tự đặt lịch phỏng vấn.')
bullet('Nhà tuyển dụng quản lý công ty, tin tuyển dụng, ứng viên, lịch phỏng vấn và quota đăng tin.')
bullet('Quản trị viên duyệt nội dung, theo dõi người dùng, báo cáo vi phạm và xử lý thanh toán.')

heading('2. Những công việc tôi đã thực hiện')
table(['Nhóm công việc', 'Nội dung thực hiện và kết quả'], [
    ('Khảo sát và xác định vấn đề', 'Phân tích các bước tuyển dụng hiện có; xác định điểm nghẽn khi lọc CV và Job bằng từ khóa; đề xuất mô hình gợi ý CV - JD hai chiều.'),
    ('Phân tích nghiệp vụ', 'Xác định vai trò Ứng viên, HR và Quản trị viên; mô tả quy trình đăng tin, ứng tuyển, duyệt tin, đặt lịch, thanh toán và xử lý báo cáo.'),
    ('Thiết kế hệ thống', 'Xác định kiến trúc monolithic theo các lớp API, service, repository và database; tách tiến trình web, worker và scheduler để vận hành ổn định.'),
    ('Thiết kế giao diện', 'Thiết kế các màn hình trang chủ, đăng nhập, tìm việc, CV, gợi ý, dashboard HR, quản trị và thanh toán; đảm bảo luồng thao tác phù hợp từng vai trò.'),
    ('Định hướng AI', 'Xác định đầu vào CV/JD, kết quả cần trả về, tiêu chí xếp hạng và cách trình bày kỹ năng khớp hoặc thiếu cho người dùng.'),
    ('Tài liệu và rà soát', 'Đối chiếu yêu cầu với chức năng hiện có; mô tả kiến trúc, dữ liệu, API, cách chạy hệ thống và các giới hạn cần tiếp tục hoàn thiện.')
], [4.0, 11.6])

heading('3. Kiến trúc và cách hệ thống vận hành')
para('Hệ thống sử dụng kiến trúc monolithic: backend nghiệp vụ tập trung trong một ứng dụng FastAPI và frontend là một React SPA. Đây là một codebase thống nhất, chưa tách thành các microservice độc lập. Khi chạy bằng Docker, các tiến trình được đặt trong các container riêng để dễ vận hành: frontend, API backend, PostgreSQL, Redis, Celery worker, Celery Beat và Nginx.')
table(['Thành phần', 'Vai trò'], [
    ('React và TypeScript', 'Xây dựng giao diện web theo từng nhóm người dùng và gọi API thống nhất.'),
    ('Nginx', 'Nhận request từ trình duyệt, phân phối frontend và chuyển request API vào backend.'),
    ('FastAPI', 'Cung cấp API, xác thực JWT, phân quyền, xử lý nghiệp vụ và trả dữ liệu cho giao diện.'),
    ('PostgreSQL và pgvector', 'Lưu tài khoản, CV, Job, đơn ứng tuyển, lịch phỏng vấn, thanh toán và vector embedding.'),
    ('Redis và Celery', 'Thực hiện các công việc nền như tạo embedding, hết hạn slot, nhắc lịch và đối soát.'),
    ('Docker Compose', 'Khởi động các thành phần theo cấu hình chung, có migration database trước khi API chạy.')
], [4.3, 11.3])
para('Luồng xử lý chính: người dùng thao tác ở giao diện -> API kiểm tra đăng nhập và quyền -> service áp dụng quy tắc nghiệp vụ -> repository truy vấn database. Những công việc tốn thời gian như tính vector không chạy trực tiếp trong request; hệ thống gửi việc sang Celery sau khi dữ liệu đã được lưu thành công.')

heading('4. Cách AI hỗ trợ so khớp CV và Job')
para('Tôi nắm được luồng nghiệp vụ và nguyên lý AI ở mức thiết kế, gồm mục tiêu của từng bước, đầu vào, đầu ra và cách kết quả được dùng trong sản phẩm.')
table(['Bước', 'Cách hoạt động trong hệ thống'], [
    ('Phân tích CV', 'Đọc file PDF, DOCX hoặc TXT; trích xuất văn bản, kỹ năng, số năm kinh nghiệm, vị trí, học vấn và các phần của CV.'),
    ('Chuẩn hóa profile', 'Chuyển CV và JD về biểu diễn ngắn gọn, nhất quán để mô hình có thể so sánh cùng loại thông tin.'),
    ('Embedding', 'Dùng mô hình multilingual E5 để biến nội dung thành vector số; vector thể hiện mức độ gần nhau về ngữ nghĩa.'),
    ('Truy hồi ứng viên hoặc Job', 'Dùng cosine similarity trên pgvector để lấy tối đa 200 kết quả gần nhất trước khi xếp hạng chi tiết.'),
    ('Chấm hybrid', 'Kết hợp tín hiệu ngữ nghĩa, độ phủ kỹ năng và mức độ đáp ứng kinh nghiệm; trả về điểm, kỹ năng khớp và kỹ năng cần bổ sung.'),
    ('Hiển thị kết quả', 'Ứng viên nhận gợi ý Job; HR nhận danh sách ứng viên, trong đó danh tính có thể được ẩn trước khi ứng viên nộp đơn.')
], [4.0, 11.6])
para('Kết quả nghiên cứu hiện có cho thấy mô hình E5 sau fine tune đạt NDCG@10 là 0,842; parser kỹ năng đạt F1 là 0,951 trên tập dữ liệu kiểm thử được tạo từ template. Các chỉ số này là cơ sở để lựa chọn giải pháp AI và cần tiếp tục kiểm chứng bằng CV thực tế.')

heading('5. Phần chuyên môn sâu có tham vấn hỗ trợ')
para('Tôi hiểu vai trò của dữ liệu, mô hình, database và các tiêu chí đánh giá trong hệ thống. Với các phần cần kiến thức chuyên sâu hơn, tôi trao đổi và nhận hỗ trợ từ một bạn có chuyên môn để rà soát giải pháp kỹ thuật. Việc tham vấn tập trung vào cách làm và tiêu chí kiểm tra; tôi vẫn chủ động xác định yêu cầu nghiệp vụ, yêu cầu đầu ra và cách tích hợp vào trải nghiệm người dùng.')
table(['Nội dung tham vấn', 'Phạm vi tôi nắm và cách phối hợp'], [
    ('Thu thập và chuẩn bị dữ liệu', 'Tôi nắm nguồn JD, cách sinh CV mẫu, chuẩn hóa kỹ năng và chia train/validation/test. Phần tạo tập dữ liệu, kiểm tra nhãn và xử lý chi tiết được trao đổi với người có chuyên môn.'),
    ('Huấn luyện mô hình', 'Tôi nắm mục tiêu fine tune E5, dữ liệu đầu vào, chỉ số NDCG, MRR, Recall và cách chọn checkpoint. Chi tiết loss, siêu tham số, GPU và cách chạy thí nghiệm được tham vấn để bảo đảm đúng phương pháp.'),
    ('Database và vector search', 'Tôi nắm ERD, nhóm bảng, quan hệ dữ liệu và lý do dùng pgvector. Phần tối ưu chỉ mục HNSW, migration và xử lý khác biệt môi trường được rà soát cùng người có chuyên môn.'),
    ('Kiểm thử kỹ thuật', 'Tôi nắm các luồng cần kiểm thử và tiêu chí chấp nhận. Phần cấu hình môi trường test, mock AI và kiểm tra migration được hỗ trợ rà soát.'),
    ('Triển khai', 'Tôi nắm vai trò các container và thứ tự chạy. Các vấn đề thực tế như SMTP, SePay và hạ tầng production cần tiếp tục kiểm chứng khi có tài khoản dịch vụ thật.')
], [4.2, 11.4])

heading('6. Công cụ đã sử dụng')
table(['Nhóm', 'Công cụ và mục đích'], [
    ('Thiết kế và phát triển web', 'React, TypeScript, Vite, FastAPI, Python, SQLAlchemy và Alembic.'),
    ('Dữ liệu và AI', 'Sentence Transformers, multilingual E5, NumPy, PostgreSQL, pgvector, dữ liệu JD IT và CV tổng hợp.'),
    ('Xử lý nền và triển khai', 'Redis, Celery, Docker Compose, Nginx và GitHub Actions.'),
    ('Kiểm thử', 'Pytest cho backend; kiểm tra API, migration, luồng nghiệp vụ, thanh toán demo và giao diện smoke test.'),
    ('Công cụ AI hỗ trợ lập trình', 'Mô hình AI hỗ trợ chuyển hóa yêu cầu thành gợi ý mã nguồn, giải thích lỗi, rà soát cấu trúc và tăng tốc tạo bản nháp. Các quyết định nghiệp vụ, phạm vi chức năng và kết quả đầu ra vẫn được kiểm tra theo yêu cầu đồ án.')
], [4.1, 11.5])

heading('7. Kiểm thử và đánh giá')
para('Kiểm thử được tổ chức theo nhiều mức để kiểm tra đúng nghiệp vụ và khả năng vận hành:')
bullet('Kiểm thử đơn vị và service: xác thực, phân quyền, CV, Job, ứng tuyển, đặt lịch, trạng thái đơn và thanh toán.')
bullet('Kiểm thử tích hợp: migration database, luồng API, webhook thanh toán demo, Celery task và kết nối dữ liệu.')
bullet('Kiểm thử hệ thống: các tình huống người dùng theo vai trò, kiểm tra ranh giới giữa API, service và repository.')
bullet('Smoke test giao diện: kiểm tra các trang chính và hiển thị cơ bản trên desktop hoặc mobile.')
bullet('Đánh giá AI: NDCG@10, MRR@10, Recall@20/50 cho xếp hạng; Precision, Recall, F1 cho trích xuất kỹ năng CV.')
para('Các giới hạn được ghi nhận gồm: parser chưa xử lý tốt CV scan cần OCR; kết quả nghiên cứu dùng nhiều CV tổng hợp; thanh toán và SMTP thật cần xác minh trên môi trường production.')

heading('8. Hướng phát triển')
bullet('Bổ sung OCR cho CV dạng ảnh hoặc scan và mở rộng parser với CV có bố cục đa dạng.')
bullet('Tăng dữ liệu gán nhãn thủ công và CV thực tế đã được ẩn danh để đánh giá khách quan hơn.')
bullet('Tối ưu lại trọng số hybrid, thử Cross Encoder cho top kết quả và theo dõi chất lượng theo từng nhóm nghề.')
bullet('Chuẩn hóa sâu hơn dữ liệu hồ sơ thành các bảng học vấn, kinh nghiệm, dự án và chứng chỉ riêng.')
bullet('Xác thực end to end với SePay, SMTP, HTTPS, backup database và giám sát production.')

heading('9. Kết luận')
para('Tôi đã thực hiện phần thiết kế và tổ chức giải pháp cho JobMatch từ xác định vấn đề đến nghiệp vụ, giao diện, kiến trúc, luồng AI và kiểm thử. Tôi hiểu cách các thành phần phối hợp để tạo thành sản phẩm hoàn chỉnh. Với các nội dung có chiều sâu về huấn luyện mô hình, tối ưu vector database và cấu hình hạ tầng, tôi chủ động tham vấn chuyên môn để bảo đảm lựa chọn kỹ thuật hợp lý, đồng thời nắm được mục đích, dữ liệu vào ra, tiêu chí đánh giá và tác động của các phần đó đến hệ thống.')

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run('JobMatch - Tóm tắt công việc đồ án')
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(90, 90, 90)

doc.core_properties.title = 'Tóm tắt công việc và mức độ tham gia dự án JobMatch'
doc.core_properties.author = 'Đỗ Trịnh Lệ Quyên'
doc.save(OUT)
print(OUT)
