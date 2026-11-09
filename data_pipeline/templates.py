"""Kho câu mẫu để ghép CV. Mỗi mục có bản tiếng Việt (vi) và tiếng Anh (en)."""

SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
            "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trịnh", "Mai", "Tạ"]
MIDDLE = ["Văn", "Thị", "Minh", "Đức", "Thu", "Ngọc", "Hoàng", "Quang", "Thanh", "Hữu",
          "Anh", "Bảo", "Gia", "Khánh", "Tuấn", "Hải", "Phương", "Xuân", "Trọng", "Lệ"]
GIVEN = ["An", "Bình", "Châu", "Dũng", "Duy", "Giang", "Hà", "Hải", "Hiếu", "Hòa", "Hùng",
         "Huy", "Khoa", "Lan", "Linh", "Long", "Mai", "Minh", "Nam", "Ngân", "Nhung", "Phong",
         "Phúc", "Quân", "Quyên", "Sơn", "Tâm", "Thảo", "Thắng", "Trang", "Trung", "Tú", "Tùng",
         "Uyên", "Việt", "Vy", "Yến", "Đạt", "Khải", "Nhật"]

UNIVERSITIES = [
    "Đại học Bách khoa Hà Nội", "Trường Đại học Công nghệ - ĐHQGHN",
    "Học viện Công nghệ Bưu chính Viễn thông", "Trường Đại học Phenikaa",
    "Trường Đại học Bách khoa - ĐHQG TP.HCM", "Trường Đại học Khoa học Tự nhiên - ĐHQG TP.HCM",
    "Trường Đại học Công nghệ Thông tin - ĐHQG TP.HCM", "Trường Đại học FPT",
    "Trường Đại học Bách khoa - Đại học Đà Nẵng", "Trường Đại học Thủy lợi",
    "Trường Đại học Công nghiệp Hà Nội", "Học viện Kỹ thuật Mật mã",
    "Trường Đại học Sư phạm Kỹ thuật TP.HCM", "Trường Đại học Cần Thơ",
]
MAJORS = {
    "default": [("Công nghệ thông tin", "Information Technology"),
                ("Khoa học máy tính", "Computer Science"),
                ("Kỹ thuật phần mềm", "Software Engineering"),
                ("Hệ thống thông tin", "Information Systems")],
    "embedded": [("Kỹ thuật điện tử - viễn thông", "Electronics and Telecommunications"),
                 ("Kỹ thuật máy tính", "Computer Engineering")],
    "ai_ml": [("Khoa học máy tính", "Computer Science"), ("Khoa học dữ liệu", "Data Science"),
              ("Toán tin", "Mathematics and Computer Science")],
    "data_analyst": [("Khoa học dữ liệu", "Data Science"), ("Hệ thống thông tin quản lý", "Management Information Systems"),
                     ("Thống kê", "Statistics")],
    "business_analyst": [("Hệ thống thông tin quản lý", "Management Information Systems"),
                         ("Công nghệ thông tin", "Information Technology")],
    "security": [("An toàn thông tin", "Information Security"), ("Công nghệ thông tin", "Information Technology")],
}

COMPANY_PARTS = ["Sao Việt", "Minh Phát", "Hòa Bình", "An Khang", "Đông Á", "Thành Công", "Tân Tiến",
                 "Nam Long", "Bình Minh", "Hưng Thịnh", "Phú Quý", "Việt Tín", "Kim Sơn", "Ánh Dương",
                 "Blue Ocean", "NextWave", "Skyline", "Brightsoft", "CodeNest", "Pixel Forge", "DataHive",
                 "CloudPeak", "Greenfield", "Lotus", "Mekong", "Red River", "Silverline", "Orbit"]
COMPANY_SUFFIX_VI = ["Công ty TNHH {x} Software", "Công ty Cổ phần Công nghệ {x}", "Công ty TNHH Giải pháp {x}",
                     "Công ty Cổ phần {x} Tech", "Công ty TNHH Phần mềm {x}"]
COMPANY_SUFFIX_EN = ["{x} Software JSC", "{x} Technology Co., Ltd", "{x} Solutions", "{x} Tech", "{x} Digital"]

DOMAINS = [("thương mại điện tử", "e-commerce"), ("ngân hàng số", "digital banking"),
           ("quản lý nhân sự", "HR management"), ("logistics và vận tải", "logistics"),
           ("y tế", "healthcare"), ("học trực tuyến", "e-learning"), ("ví điện tử", "e-wallet"),
           ("bất động sản", "real estate"), ("đặt vé du lịch", "travel booking"),
           ("nhà thông minh", "smart home"), ("bảo hiểm", "insurance"), ("bán lẻ", "retail"),
           ("quản lý kho", "warehouse management"), ("mạng xã hội", "social network"),
           ("chứng khoán", "securities trading"), ("CRM", "CRM")]

TITLE_PREFIX = {
    "intern": ("Thực tập sinh", "Intern"), "fresher": ("Fresher", "Fresher"),
    "junior": ("Junior", "Junior"), "middle": ("", ""),
    "senior": ("Senior", "Senior"), "lead": ("Lead", "Lead"),
}

# Hoạt động đặc trưng theo vai trò. {d} = lĩnh vực, {s} = kỹ năng.
ROLE_ACTIVITIES = {
    "backend": [
        ("Thiết kế và phát triển RESTful API cho hệ thống {d} bằng {s}", "Designed and built RESTful APIs for a {d} platform using {s}"),
        ("Xây dựng các service xử lý nghiệp vụ và tích hợp cơ sở dữ liệu {s}", "Implemented business services and database layer with {s}"),
        ("Tối ưu truy vấn và cache bằng {s}, giảm {p}% thời gian phản hồi", "Optimized queries and caching with {s}, cutting response time by {p}%"),
        ("Tách hệ thống monolith thành microservices sử dụng {s}", "Split a monolith into microservices using {s}"),
        ("Xây dựng hàng đợi xử lý bất đồng bộ với {s}", "Built asynchronous processing pipelines with {s}"),
    ],
    "frontend": [
        ("Phát triển giao diện web cho hệ thống {d} bằng {s}", "Developed the web UI of a {d} system with {s}"),
        ("Xây dựng thư viện component dùng chung với {s}", "Built a shared component library with {s}"),
        ("Tối ưu hiệu năng tải trang, cải thiện Lighthouse score thêm {p}%", "Improved page-load performance, raising Lighthouse score by {p}%"),
        ("Chuyển đổi thiết kế Figma thành giao diện responsive bằng {s}", "Turned Figma designs into responsive pages using {s}"),
        ("Quản lý state và tích hợp API backend với {s}", "Handled state management and API integration with {s}"),
    ],
    "fullstack": [
        ("Phát triển end-to-end các tính năng của ứng dụng {d} với {s}", "Delivered end-to-end features for a {d} app with {s}"),
        ("Xây dựng API phía server và giao diện quản trị bằng {s}", "Built server-side APIs and an admin dashboard using {s}"),
        ("Triển khai ứng dụng lên môi trường cloud với {s}", "Deployed the application to the cloud with {s}"),
        ("Thiết kế cơ sở dữ liệu và luồng xác thực người dùng dùng {s}", "Designed the database schema and auth flow with {s}"),
    ],
    "mobile": [
        ("Phát triển ứng dụng di động {d} trên Android/iOS bằng {s}", "Built a {d} mobile app for Android/iOS with {s}"),
        ("Tích hợp push notification, thanh toán và API backend với {s}", "Integrated push notifications, payments and backend APIs using {s}"),
        ("Giảm {p}% crash rate và tối ưu thời gian khởi động ứng dụng", "Reduced crash rate by {p}% and improved app start-up time"),
        ("Đưa ứng dụng lên App Store/Google Play, bảo trì các phiên bản mới với {s}", "Published and maintained releases on App Store/Google Play using {s}"),
    ],
    "qa_tester": [
        ("Viết test case và thực hiện kiểm thử chức năng cho hệ thống {d}", "Wrote test cases and ran functional testing for a {d} system"),
        ("Xây dựng bộ kiểm thử tự động bằng {s}", "Built automated test suites with {s}"),
        ("Kiểm thử API và hiệu năng với {s}", "Performed API and performance testing using {s}"),
        ("Quản lý bug và báo cáo chất lượng trên {s}, giảm {p}% lỗi lọt lên production", "Tracked bugs in {s}, reducing production defects by {p}%"),
    ],
    "devops_cloud": [
        ("Xây dựng pipeline CI/CD cho các dự án {d} với {s}", "Built CI/CD pipelines for {d} projects with {s}"),
        ("Quản lý hạ tầng cloud và Infrastructure as Code bằng {s}", "Managed cloud infrastructure as code with {s}"),
        ("Container hóa và vận hành cụm dịch vụ bằng {s}", "Containerized and operated services using {s}"),
        ("Thiết lập giám sát, cảnh báo với {s}, nâng uptime lên 99.9%", "Set up monitoring and alerting with {s}, reaching 99.9% uptime"),
    ],
    "security": [
        ("Đánh giá bảo mật, pentest ứng dụng web cho hệ thống {d}", "Performed security assessments and web pentests for a {d} system"),
        ("Vận hành SIEM và phân tích log sự cố với {s}", "Operated SIEM and analyzed incident logs using {s}"),
        ("Xây dựng chính sách bảo mật và hardening máy chủ {s}", "Defined security policies and hardened {s} servers"),
    ],
    "ai_ml": [
        ("Huấn luyện và triển khai mô hình học máy cho bài toán {d} bằng {s}", "Trained and deployed ML models for {d} use cases with {s}"),
        ("Xây dựng pipeline xử lý dữ liệu và feature engineering với {s}", "Built data processing and feature engineering pipelines with {s}"),
        ("Fine-tune mô hình deep learning, tăng độ chính xác thêm {p}%", "Fine-tuned deep learning models, improving accuracy by {p}%"),
        ("Đóng gói mô hình thành API phục vụ production bằng {s}", "Served models as production APIs using {s}"),
    ],
    "data_engineer": [
        ("Xây dựng pipeline ETL cho kho dữ liệu {d} bằng {s}", "Built ETL pipelines for a {d} data warehouse with {s}"),
        ("Xử lý dữ liệu lớn theo batch và streaming với {s}", "Processed big data in batch and streaming mode with {s}"),
        ("Thiết kế data model và tối ưu truy vấn trên {s}", "Designed data models and tuned queries on {s}"),
    ],
    "data_analyst": [
        ("Phân tích dữ liệu kinh doanh mảng {d} và xây dựng dashboard bằng {s}", "Analyzed {d} business data and built dashboards with {s}"),
        ("Viết truy vấn {s} trích xuất báo cáo định kỳ", "Wrote {s} queries for recurring reports"),
        ("Đề xuất insight giúp tăng {p}% tỉ lệ chuyển đổi", "Delivered insights that lifted conversion by {p}%"),
    ],
    "business_analyst": [
        ("Thu thập, phân tích yêu cầu và viết tài liệu SRS cho hệ thống {d}", "Gathered requirements and wrote SRS documents for a {d} system"),
        ("Vẽ quy trình nghiệp vụ, wireframe và user story trên {s}", "Modeled business processes, wireframes and user stories in {s}"),
        ("Làm cầu nối giữa khách hàng và đội phát triển trong mô hình {s}", "Acted as the bridge between clients and developers under {s}"),
    ],
    "project_manager": [
        ("Quản lý dự án {d} với đội {n} thành viên theo {s}", "Managed a {d} project with a team of {n} under {s}"),
        ("Lập kế hoạch, theo dõi tiến độ và rủi ro trên {s}", "Planned sprints and tracked progress and risks in {s}"),
        ("Đàm phán phạm vi với khách hàng, bàn giao đúng hạn {p}% milestone", "Negotiated scope with clients and hit {p}% of milestones on time"),
    ],
    "game": [
        ("Phát triển gameplay và hệ thống nhân vật bằng {s}", "Developed gameplay and character systems with {s}"),
        ("Tối ưu hiệu năng render, tăng {p}% FPS trên thiết bị yếu", "Optimized rendering, gaining {p}% FPS on low-end devices"),
        ("Tích hợp quảng cáo, in-app purchase và analytics với {s}", "Integrated ads, in-app purchases and analytics using {s}"),
    ],
    "embedded": [
        ("Lập trình firmware cho vi điều khiển trong thiết bị {d} bằng {s}", "Wrote firmware for microcontrollers in {d} devices using {s}"),
        ("Phát triển driver giao tiếp ngoại vi và giao thức truyền thông với {s}", "Developed peripheral drivers and communication protocols with {s}"),
        ("Debug phần cứng, tối ưu tiêu thụ năng lượng giảm {p}%", "Debugged hardware and cut power consumption by {p}%"),
    ],
    "blockchain": [
        ("Viết và audit smart contract bằng {s}", "Wrote and audited smart contracts in {s}"),
        ("Xây dựng DApp và tích hợp ví với {s}", "Built DApps and wallet integrations using {s}"),
        ("Phát triển backend đọc dữ liệu on-chain bằng {s}", "Built backend services indexing on-chain data with {s}"),
    ],
    "software_engineer": [
        ("Phát triển và bảo trì các module phần mềm cho hệ thống {d} bằng {s}", "Developed and maintained software modules for a {d} system using {s}"),
        ("Phân tích yêu cầu, thiết kế và hiện thực tính năng mới với {s}", "Analyzed requirements, designed and implemented features with {s}"),
        ("Viết unit test, sửa lỗi và cải thiện chất lượng mã nguồn {s}", "Wrote unit tests, fixed bugs and improved {s} code quality"),
    ],
}

GENERIC_BULLETS = [
    ("Viết unit test và tài liệu kỹ thuật cho các module phụ trách", "Wrote unit tests and technical documentation for owned modules"),
    ("Tham gia code review và các buổi họp sprint", "Took part in code reviews and sprint ceremonies"),
    ("Phối hợp với BA và tester để làm rõ yêu cầu", "Worked with BAs and testers to clarify requirements"),
    ("Sử dụng {s} trong quy trình làm việc hằng ngày", "Used {s} in the daily workflow"),
    ("Làm việc với {s} trong môi trường production", "Worked with {s} in production"),
]
SENIOR_BULLETS = [
    ("Dẫn dắt nhóm {n} người, hướng dẫn các thành viên junior", "Led a team of {n} engineers and mentored junior members"),
    ("Đề xuất kiến trúc và review thiết kế kỹ thuật", "Proposed architecture and reviewed technical designs"),
    ("Làm việc trực tiếp với khách hàng để ước lượng và chốt giải pháp", "Worked directly with clients on estimation and solution design"),
]

SUMMARY = [
    ("{title} với {y} năm kinh nghiệm, thế mạnh về {s}. Mong muốn phát triển trong môi trường chuyên nghiệp.",
     "{title} with {y} years of experience, strong in {s}. Looking for a professional environment to grow."),
    ("Có {y} năm kinh nghiệm làm {title}, thành thạo {s}. Mục tiêu trở thành chuyên gia trong lĩnh vực trong 2-3 năm tới.",
     "{y} years working as a {title}, proficient in {s}. Aiming to become a domain expert within 2-3 years."),
    ("Đam mê công nghệ, {y} năm kinh nghiệm thực tế với {s}. Sẵn sàng học hỏi và đóng góp cho sản phẩm.",
     "Passionate engineer with {y} years of hands-on experience in {s}. Eager to learn and contribute to the product."),
]
SUMMARY_NEWBIE = [
    ("Sinh viên mới tốt nghiệp, đã có kiến thức về {s} qua đồ án và dự án cá nhân. Mong muốn được làm {title}.",
     "Recent graduate with knowledge of {s} gained through coursework and personal projects. Seeking a {title} role."),
    ("Mong muốn trở thành {title}, đã tự học và làm dự án với {s}.",
     "Aspiring {title}, self-taught and built projects with {s}."),
]

PROJECT_NAMES = [("Hệ thống quản lý {d}", "{d} management system"), ("Ứng dụng {d}", "{d} application"),
                 ("Nền tảng {d}", "{d} platform"), ("Cổng thông tin {d}", "{d} portal")]

CERTS = {
    "AWS": "AWS Certified Solutions Architect - Associate",
    "Azure": "Microsoft Certified: Azure Fundamentals",
    "GCP": "Google Cloud Associate Cloud Engineer",
    "Kubernetes": "Certified Kubernetes Administrator (CKA)",
    "Java": "Oracle Certified Professional, Java SE",
    "Agile/Scrum": "Professional Scrum Master I (PSM I)",
}
ROLE_CERTS = {"qa_tester": "ISTQB Foundation Level", "project_manager": "PMP",
              "security": "CompTIA Security+", "business_analyst": "IIBA ECBA"}
LANG_CERTS = ["TOEIC 750", "TOEIC 850", "IELTS 6.5", "IELTS 7.0", "JLPT N3", "JLPT N2"]

SECTION_TITLES = {
    "summary": ("MỤC TIÊU NGHỀ NGHIỆP", "SUMMARY"),
    "skills": ("KỸ NĂNG", "SKILLS"),
    "experience": ("KINH NGHIỆM LÀM VIỆC", "WORK EXPERIENCE"),
    "projects": ("DỰ ÁN", "PROJECTS"),
    "education": ("HỌC VẤN", "EDUCATION"),
    "certs": ("CHỨNG CHỈ", "CERTIFICATIONS"),
}
