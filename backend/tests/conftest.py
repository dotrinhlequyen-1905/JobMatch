"""Test chạy trên DB riêng recruit_ai_test, embedder hashing (nhanh, không cần GPU)."""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./jobmatch_test.db")
from sqlalchemy.engine import make_url

test_database = make_url(os.environ["DATABASE_URL"]).database or ""
if test_database != ":memory:" and "test" not in test_database.lower():
    raise RuntimeError("TEST_DATABASE_URL must point to a separate database with 'test' in its name")
os.environ["EMBED_MODEL"] = "hashing"
os.environ["CROSS_ENCODER_MODEL"] = ""
os.environ["TASK_ALWAYS_EAGER"] = "true"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["SEPAY_WEBHOOK_KEY"] = "dev-sepay-key"
os.environ["ENABLE_DEV_TOOLS"] = "true"
# Không bao giờ gửi email thật khi test, kể cả khi .env đã cấu hình SMTP; email được ghi vào mailer.outbox.
os.environ["SMTP_HOST"] = ""
import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import Package, User
from app.core.security import hash_password


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(email="admin@t.vn", password_hash=hash_password("123456"), full_name="Admin", role="ADMIN"))
        db.add_all(
            [
                Package(code="HR_BASIC", name="HR basic", target="HR", price=199000, duration_days=30, quota_jobs=5),
                Package(code="CAND", name="Premium", target="CANDIDATE", price=49000, duration_days=30),
            ]
        )
        db.commit()
    with TestClient(app) as c:
        yield c


def login(c, email, pw="123456"):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def register(c, email, role, company=None):
    r = c.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "123456",
            "full_name": email.split("@")[0],
            "role": role,
            "company_name": company,
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


CV_TEXT = "NGUYEN VAN A\nBackend Developer\na@gmail.com | 0912345678 | Hà Nội\n\nKINH NGHIỆM LÀM VIỆC\nBackend Developer | ABC | 2021 - Hiện tại\n- Phát triển RESTful API bằng Java, Spring Boot, PostgreSQL, Docker\n\nKỸ NĂNG\nJava, Spring Boot, PostgreSQL, Docker, Redis, Git\n"


@pytest.fixture()
def world(client):
    """HR đã duyệt công ty + 1 tin đã duyệt; 2 ứng viên có CV."""
    c = client
    admin = login(c, "admin@t.vn")
    hr = register(c, "hr@t.vn", "HR", "Công ty T")
    cid = c.get("/api/v1/companies/me", headers=hr).json()["id"]
    assert (
        c.post(f"/api/v1/admin/companies/{cid}/review", json={"status": "APPROVED"}, headers=admin).status_code == 200
    )
    job = c.post(
        "/api/v1/jobs",
        headers=hr,
        json={
            "title": "Java Backend Developer",
            "min_years": 2,
            "description": "Yêu cầu 2 năm kinh nghiệm Java, Spring Boot, PostgreSQL, Docker, Kafka. Làm việc tại Hà Nội.",
        },
    ).json()
    assert (
        c.patch(f"/api/v1/admin/jobs/{job['id']}/moderate", json={"status": "PUBLISHED"}, headers=admin).status_code
        == 200
    )
    cands = []
    for i in range(2):
        h = register(c, f"uv{i}@t.vn", "CANDIDATE")
        r = c.post("/api/v1/cvs", data={"text": CV_TEXT}, headers=h)
        assert r.status_code == 200, r.text
        cands.append(h)
    return {"c": c, "admin": admin, "hr": hr, "job": job, "cands": cands}
