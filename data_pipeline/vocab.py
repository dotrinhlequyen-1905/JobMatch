"""Từ điển kỹ năng, vai trò và các hàm chuẩn hóa dùng chung cho toàn pipeline."""
import re

# ---------------------------------------------------------------------------
# 1. Chuẩn hóa kỹ năng
# ---------------------------------------------------------------------------
# key = tên kỹ năng viết thường, bỏ ký tự đặc biệt (giữ + và #)
# value = tên chuẩn. Các biến thể có cùng key tự động gộp, bảng này xử lý
# các trường hợp khác key nhưng cùng nghĩa.
ALIASES = {
    "react": "React", "reactjs": "React",
    "reactnative": "React Native",
    "vue": "Vue.js", "vuejs": "Vue.js", "vue3": "Vue.js", "vue2": "Vue.js",
    "angular": "Angular", "angularjs": "Angular",
    "nodejs": "Node.js", "node": "Node.js",
    "nextjs": "Next.js", "next": "Next.js",
    "nuxtjs": "Nuxt.js", "nuxt": "Nuxt.js",
    "nestjs": "NestJS",
    "express": "Express.js", "expressjs": "Express.js",
    "go": "Go", "golang": "Go",
    "html": "HTML/CSS", "css": "HTML/CSS", "htmlcss": "HTML/CSS", "html5": "HTML/CSS",
    "css3": "HTML/CSS", "html5css3": "HTML/CSS",
    "sass": "SASS", "scss": "SASS",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS",
    "jquery": "jQuery",
    "restfulapis": "RESTful API", "restfulapi": "RESTful API", "restful": "RESTful API",
    "rest": "RESTful API", "restapi": "RESTful API", "restapis": "RESTful API",
    "webapi": "RESTful API", "api": "RESTful API", "apis": "RESTful API",
    "cicd": "CI/CD",
    "git": "Git", "github": "Git", "gitlab": "Git", "bitbucket": "Git",
    "githubactions": "GitHub Actions", "gitlabci": "GitLab CI",
    "aws": "AWS", "amazonwebservices": "AWS",
    "gcp": "GCP", "googlecloud": "GCP", "googlecloudplatform": "GCP",
    "azure": "Azure", "microsoftazure": "Azure",
    "k8s": "Kubernetes",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mssql": "SQL Server", "sqlserver": "SQL Server", "mssqlserver": "SQL Server",
    "microsoftsqlserver": "SQL Server",
    "oracle": "Oracle", "oracledatabase": "Oracle", "oracledb": "Oracle",
    "plsql": "PL/SQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "elasticsearch": "Elasticsearch", "elk": "Elasticsearch",
    "kafka": "Kafka", "apachekafka": "Kafka",
    "spark": "Spark", "apachespark": "Spark", "pyspark": "Spark",
    "springboot": "Spring Boot",
    "spring": "Spring", "springframework": "Spring", "springmvc": "Spring",
    "net": ".NET", "netcore": ".NET", "netframework": ".NET", "aspnet": ".NET",
    "aspnetcore": ".NET", "aspnetmvc": ".NET", "dotnet": ".NET", "dotnetcore": ".NET",
    "entityframework": "Entity Framework",
    "c": "C", "c++": "C++", "cc++": "C/C++",
    "objectivec": "Objective-C",
    "jira": "Jira", "confluence": "Confluence",
    "scrum": "Agile/Scrum", "agile": "Agile/Scrum", "agilescrum": "Agile/Scrum", "kanban": "Agile/Scrum",
    "machinelearning": "Machine Learning", "ml": "Machine Learning",
    "deeplearning": "Deep Learning", "dl": "Deep Learning",
    "llm": "LLM", "llms": "LLM", "genai": "LLM", "generativeai": "LLM",
    "nlp": "NLP", "computervision": "Computer Vision", "cv": "Computer Vision",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "keras": "Keras",
    "scikitlearn": "Scikit-learn", "sklearn": "Scikit-learn",
    "powerbi": "Power BI", "tableau": "Tableau",
    "rubyonrails": "Ruby on Rails", "rails": "Ruby on Rails",
    "unity": "Unity", "unity3d": "Unity", "unrealengine": "Unreal Engine", "unreal": "Unreal Engine",
    "linux": "Linux", "embeddedlinux": "Embedded Linux",
    "rtos": "RTOS", "freertos": "RTOS",
    "selenium": "Selenium", "appium": "Appium", "playwright": "Playwright", "cypress": "Cypress",
    "jmeter": "JMeter", "postman": "Postman",
    "junit": "JUnit", "jest": "Jest",
    "swiftui": "SwiftUI", "jetpackcompose": "Jetpack Compose",
    "redux": "Redux", "graphql": "GraphQL", "grpc": "gRPC",
    "microservices": "Microservices", "microservice": "Microservices",
    "docker": "Docker", "terraform": "Terraform", "ansible": "Ansible", "jenkins": "Jenkins",
    "nginx": "Nginx", "redis": "Redis", "rabbitmq": "RabbitMQ",
    "figma": "Figma", "adobexd": "Adobe XD",
    "web3": "Web3", "web3js": "Web3", "blockchain": "Blockchain", "solidity": "Solidity",
    "etl": "ETL", "airflow": "Airflow", "apacheairflow": "Airflow",
    "hadoop": "Hadoop", "databricks": "Databricks",
    "pandas": "Pandas", "numpy": "NumPy",
    "langchain": "LangChain", "opencv": "OpenCV",
    "typescript": "TypeScript", "ts": "TypeScript",
    "javascript": "JavaScript", "js": "JavaScript", "es6": "JavaScript",
}

# Nhãn rỗng / quá chung chung / không phải kỹ năng IT -> bỏ
DROP = {
    "notspecified", "none", "na", "", "cloud", "ai", "it", "software", "web",
    "windows", "slack", "trello", "saas", "erp", "json", "xml", "oop",
    "mastercam", "cnc", "autocad", "nx", "solidworks", "photoshop",
}

# Biến thể viết khác để CV sinh ra dùng (dạy mô hình biết ReactJS == React ...)
SURFACE_VARIANTS = {
    "React": ["React", "ReactJS", "React.js"],
    "Vue.js": ["Vue.js", "VueJS", "Vue 3"],
    "Node.js": ["Node.js", "NodeJS", "Node"],
    "Next.js": ["Next.js", "NextJS"],
    "Go": ["Go", "Golang"],
    "HTML/CSS": ["HTML/CSS", "HTML5, CSS3", "HTML & CSS"],
    "RESTful API": ["RESTful API", "REST API", "Web API", "RESTful services"],
    "CI/CD": ["CI/CD", "CICD", "continuous integration/deployment"],
    "PostgreSQL": ["PostgreSQL", "Postgres"],
    "SQL Server": ["SQL Server", "MSSQL", "MS SQL Server"],
    "Kubernetes": ["Kubernetes", "K8s"],
    ".NET": [".NET", ".NET Core", "ASP.NET Core", "C# .NET"],
    "Spring": ["Spring", "Spring Framework", "Spring MVC"],
    "Agile/Scrum": ["Agile/Scrum", "Scrum", "Agile"],
    "Machine Learning": ["Machine Learning", "ML", "học máy"],
    "Deep Learning": ["Deep Learning", "học sâu"],
    "Computer Vision": ["Computer Vision", "thị giác máy tính"],
    "NLP": ["NLP", "xử lý ngôn ngữ tự nhiên"],
    "GCP": ["GCP", "Google Cloud"],
    "AWS": ["AWS", "Amazon Web Services"],
    "Git": ["Git", "Git/GitHub", "GitLab"],
    "Tailwind CSS": ["Tailwind CSS", "TailwindCSS"],
    "Scikit-learn": ["Scikit-learn", "sklearn"],
    "JavaScript": ["JavaScript", "JS", "ES6+"],
    "TypeScript": ["TypeScript", "TS"],
    "LLM": ["LLM", "Generative AI", "GenAI"],
    "Kafka": ["Kafka", "Apache Kafka"],
    "Spark": ["Spark", "PySpark", "Apache Spark"],
}


def skill_key(s: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", s.lower())


def normalize_skill(s: str):
    """Trả về tên chuẩn của kỹ năng, hoặc None nếu cần bỏ."""
    k = skill_key(s)
    if k in DROP:
        return None
    if k in ALIASES:
        return ALIASES[k]
    return s.strip()


# ---------------------------------------------------------------------------
# 2. Chuẩn hóa vai trò (329 loại -> ~15 nhóm)
# ---------------------------------------------------------------------------
# Thứ tự quan trọng: luật đứng trước được ưu tiên.
ROLE_RULES = [
    ("qa_tester",       r"\bqa\b|qc|test|tester|kiểm thử|quality"),
    ("devops_cloud",    r"devops|sre|cloud|site reliability|platform engineer|system engineer|hệ thống|infrastructure|network|mạng"),
    ("security",        r"secur|bảo mật|an ninh|pentest|soc\b|cyber"),
    ("ai_ml",           r"\bai\b|machine learning|vision|speech|\bml\b|deep learning|computer vision|nlp|llm|data scien|trí tuệ nhân tạo"),
    ("data_engineer",   r"data engineer|big data|etl|kỹ sư dữ liệu|database|dba"),
    ("data_analyst",    r"data analy|\bbi\b|business intelligence|phân tích dữ liệu"),
    ("business_analyst", r"business analy|\bba\b|phân tích nghiệp vụ"),
    ("project_manager", r"project manager|\bpm\b|product manager|product owner|scrum master|quản lý dự án|it manager|delivery"),
    ("mobile",          r"mobile|android|ios|flutter|react native|swift|kotlin"),
    ("game",            r"game|unity|unreal|cocos"),
    ("embedded",        r"embedded|nhúng|firmware|iot|c/c\+\+|c\+\+|autosar|plc|automotive"),
    ("blockchain",      r"blockchain|web3|solidity|smart contract"),
    ("fullstack",       r"full[- ]?stack"),
    ("frontend",        r"front[- ]?end|ui developer|reactjs|react developer|vue|angular|web developer"),
    ("backend",         r"back[- ]?end|java|\.net|php|golang|\bgo\b|python|node|ruby|odoo|c#|api"),
    ("software_engineer", r"software|developer|engineer|lập trình|programmer|tech lead|technical lead|architect|kỹ sư"),
]

ROLE_DISPLAY = {  # (tiếng Việt, tiếng Anh)
    "backend": ("Lập trình viên Backend", "Backend Developer"),
    "frontend": ("Lập trình viên Frontend", "Frontend Developer"),
    "fullstack": ("Lập trình viên Full-stack", "Full-stack Developer"),
    "mobile": ("Lập trình viên Mobile", "Mobile Developer"),
    "qa_tester": ("Kỹ sư kiểm thử phần mềm", "QA/QC Engineer"),
    "devops_cloud": ("Kỹ sư DevOps", "DevOps Engineer"),
    "security": ("Kỹ sư bảo mật", "Security Engineer"),
    "ai_ml": ("Kỹ sư AI", "AI/ML Engineer"),
    "data_engineer": ("Kỹ sư dữ liệu", "Data Engineer"),
    "data_analyst": ("Chuyên viên phân tích dữ liệu", "Data Analyst"),
    "business_analyst": ("Chuyên viên phân tích nghiệp vụ", "Business Analyst"),
    "project_manager": ("Quản lý dự án CNTT", "IT Project Manager"),
    "game": ("Lập trình viên Game", "Game Developer"),
    "embedded": ("Kỹ sư phần mềm nhúng", "Embedded Engineer"),
    "blockchain": ("Lập trình viên Blockchain", "Blockchain Developer"),
    "software_engineer": ("Kỹ sư phần mềm", "Software Engineer"),
}

# Các nhóm "gần nhau" -> CV của nhóm này ứng tuyển JD nhóm kia được coi là
# phù hợp một phần chứ không phải hoàn toàn không phù hợp.
RELATED_ROLES = {
    "backend": {"fullstack", "software_engineer"},
    "frontend": {"fullstack", "software_engineer"},
    "fullstack": {"backend", "frontend", "software_engineer"},
    "software_engineer": {"backend", "frontend", "fullstack", "mobile", "embedded"},
    "mobile": {"software_engineer"},
    "data_engineer": {"data_analyst", "ai_ml", "backend"},
    "data_analyst": {"data_engineer", "business_analyst"},
    "ai_ml": {"data_engineer"},
    "devops_cloud": {"backend"},
    "business_analyst": {"project_manager", "data_analyst"},
    "project_manager": {"business_analyst"},
    "embedded": {"software_engineer"},
    "game": {"software_engineer"},
    "blockchain": {"backend"},
    "qa_tester": set(),
    "security": {"devops_cloud"},
}


def normalize_role(raw_role: str, title: str) -> str:
    for text in (raw_role, title):
        t = str(text).lower()
        for role, pattern in ROLE_RULES:
            if re.search(pattern, t):
                return role
    return "other"


# ---------------------------------------------------------------------------
# 3. Cấp bậc và số năm kinh nghiệm
# ---------------------------------------------------------------------------
SENIORITY_RULES = [  # lấy cấp thấp nhất khi tiêu đề ghi khoảng, vd "[Middle, Senior]"
    ("intern", r"intern|thực tập"),
    ("fresher", r"fresher|mới tốt nghiệp"),
    ("junior", r"junior|\bjr\b"),
    ("middle", r"middle|mid[- ]level|\bmid\b"),
    ("senior", r"senior|\bsr\b|cao cấp"),
    ("lead", r"lead|leader|trưởng nhóm|principal|architect|manager|head"),
]
SENIORITY_YEARS = {"intern": 0, "fresher": 0, "junior": 1, "middle": 2, "senior": 4, "lead": 5}


def seniority_from_title(title: str):
    t = title.lower()
    for level, pattern in SENIORITY_RULES:
        if re.search(pattern, t):
            return level
    return None


YEARS_RE = re.compile(
    r"(?:(?:ít nhất|tối thiểu|at least|minimum|min\.?|trên|over)\s*)?"
    r"(\d{1,2})\s*(?:\+|-\s*\d{1,2}|~\s*\d{1,2})?\s*"
    r"(?:năm|years?|yrs?)\b[^.\n]{0,40}?(?:kinh nghiệm|experience|exp\b|kn\b|of|trong|làm việc|in)",
    re.IGNORECASE,
)


def min_years_from_text(text: str):
    vals = [int(m.group(1)) for m in YEARS_RE.finditer(text)]
    vals = [v for v in vals if 0 < v <= 15]
    return min(vals) if vals else None


def years_to_seniority(y: int) -> str:
    if y <= 0:
        return "fresher"
    if y <= 1:
        return "junior"
    if y <= 3:
        return "middle"
    if y <= 5:
        return "senior"
    return "lead"
