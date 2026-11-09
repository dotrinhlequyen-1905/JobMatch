"""Nạp dữ liệu demo từ data/final vào DB.

  python backend/scripts/seed.py    # nạp vào DB trống đã migration
  python backend/scripts/seed.py --reset  # chủ động xóa dữ liệu demo rồi nạp lại
  python scripts/seed.py --reembed  # chỉ tính lại embedding (sau khi đổi/huấn luyện model)

Tài khoản demo (mật khẩu 123456): admin@demo.vn, hr@demo.vn, candidate@demo.vn
Các tài khoản HR/ứng viên sinh từ dữ liệu cũng có mật khẩu 123456.
"""

import argparse
import json
import random
import sys
import unicodedata
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, text  # noqa: E402

from app.ai.embedder import get_embedder, to_bytes  # noqa: E402
from app.config import ROOT_DIR  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.company_logos import catalog_company_logo_url  # noqa: E402
from app.models import (
    CV,
    Application,
    ApplicationHistory,
    Company,
    InterviewSlot,
    Job,
    Package,  # noqa: E402
    User,
)
from app.core.security import hash_password  # noqa: E402
from app.core.package_catalog import CANDIDATE_PREMIUM_PACKAGES  # noqa: E402
from app.services.common import cv_text, job_text, now  # noqa: E402

rng = random.Random(2026)
PASSWORD = "123456"
PACKAGES = [
    ("HR_BASIC", "Gói đăng tin Cơ bản", "HR", 199000, 30, 5, "5 tin tuyển dụng trong 30 ngày"),
    ("HR_PRO", "Gói đăng tin Chuyên nghiệp", "HR", 499000, 60, 20, "20 tin tuyển dụng trong 60 ngày"),
    *CANDIDATE_PREMIUM_PACKAGES,
]
SALARY = {
    "intern": (3, 6),
    "fresher": (7, 12),
    "junior": (12, 20),
    "middle": (20, 35),
    "senior": (35, 60),
    "lead": (50, 90),
}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return "".join(c if c.isalnum() else "" for c in s)[:20] or "company"


def load(name):
    return [json.loads(l) for l in open(ROOT_DIR / "data/final" / name, encoding="utf-8")]


def embed_all(db):
    emb = get_embedder()
    print(f"Tính embedding bằng: {emb.name}")
    for model, text_fn in ((Job, job_text), (CV, cv_text)):
        rows = db.scalars(select(model).order_by(model.id)).all()
        vecs = emb.encode([text_fn(r) for r in rows], batch_size=128)
        for r, v in zip(rows, vecs):
            r.embedding = to_bytes(v)
            r.embedding_model = emb.name
            r.processing_status = "READY"
            r.embedding_revision = (r.embedding_revision or 0) + 1
        db.commit()
        print(f"  {model.__tablename__}: {len(rows)}")


def seed(reset=False):
    jobs, cvs = load("jobs.jsonl"), load("cvs.jsonl")
    with SessionLocal() as db:
        populated = any(db.scalar(select(table).limit(1)) is not None for table in Base.metadata.sorted_tables)
        if populated and not reset:
            raise SystemExit("DB đã có dữ liệu. Chỉ dùng --reset nếu muốn xóa toàn bộ dữ liệu ứng dụng để nạp demo.")
        if reset:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(delete(table))
            db.commit()
    pw = hash_password(PASSWORD)  # dùng chung 1 hash cho tài khoản sinh tự động (nạp nhanh)
    with SessionLocal() as db:
        for code, name, target, price, days, quota, desc in PACKAGES:
            db.add(
                Package(
                    code=code,
                    name=name,
                    target=target,
                    price=price,
                    duration_days=days,
                    quota_jobs=quota,
                    description=desc,
                )
            )
        admin = User(email="admin@demo.vn", password_hash=pw, full_name="Quản trị viên", role="ADMIN", email_verified_at=now())
        db.add(admin)

        # --- công ty + HR từ dữ liệu JD thật
        companies, used = {}, set()
        for j in jobs:
            if j["company"] in companies:
                continue
            base = slug(j["company"])
            email, k = f"hr.{base}@demo.vn", 1
            while email in used:
                k += 1
                email = f"hr.{base}{k}@demo.vn"
            used.add(email)
            hr = User(email=email, password_hash=pw, full_name=f"HR {j['company'][:80]}", role="HR", email_verified_at=now())
            c = Company(
                owner=hr,
                name=j["company"][:250],
                logo_url=catalog_company_logo_url(j["company"]),
                location=j["city"] if j["city"] != "Not Specified" else None,
                status="APPROVED",
                description=f"{j['company']} đang tuyển dụng nhiều vị trí công nghệ tại {j['city']}.",
            )
            db.add_all([hr, c])
            companies[j["company"]] = c
        db.flush()
        # công ty có nhiều tin nhất -> tài khoản hr@demo.vn để demo
        top = max(companies, key=lambda n: sum(1 for j in jobs if j["company"] == n))
        companies[top].owner.email = "hr@demo.vn"
        companies[top].owner.full_name = "HR Demo"

        for j in jobs:
            lo, hi = SALARY.get(j["seniority"], (10, 25))
            created = now() - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))
            db.add(
                Job(
                    company_id=companies[j["company"]].id,
                    title=j["title"][:300],
                    description=j["description"],
                    role=j["role"],
                    seniority=j["seniority"],
                    min_years=j["min_years"],
                    skills=j["skills"],
                    city=j["city"] if j["city"] != "Not Specified" else None,
                    status="PUBLISHED",
                    salary_min=rng.randint(lo, (lo + hi) // 2) * 1_000_000 if rng.random() < 0.7 else None,
                    salary_max=hi * 1_000_000 if rng.random() < 0.7 else None,
                    created_at=created,
                    expires_at=created + timedelta(days=60),
                )
            )
        db.flush()
        print(f"Công ty: {len(companies)}, tin: {len(jobs)}")

        # --- ứng viên + CV tổng hợp
        for i, c in enumerate(cvs):
            email = "candidate@demo.vn" if i == 0 else f"uv{i:05d}@demo.vn"
            u = User(email=email, password_hash=pw, full_name=c["name"], phone=c["phone"], role="CANDIDATE", email_verified_at=now())
            db.add(u)
            db.add(
                CV(
                    candidate=u,
                    title=c["title"],
                    file_type="text",
                    raw_text=c["text"],
                    parsed={
                        "name": c["name"],
                        "title": c["title"],
                        "email": c["email"],
                        "phone": c["phone"],
                        "sections": {"summary": c["summary"]},
                        "experience": [
                            {"position": e["position"], "start": e["start"], "end": e["end"]} for e in c["experience"]
                        ],
                        "major": c["education"]["major"],
                    },
                    skills=c["skills"],
                    years=c["years"],
                    seniority=c["seniority"],
                    role=c["role"],
                    is_default=True,
                )
            )
        db.commit()
        print(f"Ứng viên/CV: {len(cvs)}")
        embed_all(db)
        demo_flow(db)


def demo_flow(db):
    """Tạo sẵn vài đơn ứng tuyển ở các trạng thái khác nhau + khung giờ phỏng vấn cho tài khoản hr@demo.vn."""
    from app.ai.matcher import rank_cvs_for_job

    hr = db.scalar(select(User).where(User.email == "hr@demo.vn"))
    jobs = db.scalars(select(Job).where(Job.company_id == hr.company.id).order_by(Job.id)).all()[:3]
    statuses = [
        "NEW",
        "NEW",
        "SCREENING",
        "INTERVIEW_INVITED",
        "INTERVIEW_INVITED",
        "INTERVIEW_SCHEDULED",
        "INTERVIEWED",
        "REJECTED",
    ]
    path = ["NEW", "SCREENING", "INTERVIEW_INVITED", "INTERVIEW_SCHEDULED", "INTERVIEWED"]
    for idx, job in enumerate(jobs):
        # mỗi tin 1 ngày khác nhau -> lịch của cùng HR không chồng giờ (đúng như ràng buộc khi HR tự tạo)
        start = (now() + timedelta(days=2 + idx)).replace(hour=2, minute=0, second=0, microsecond=0)  # 9h giờ VN
        slots = [
            InterviewSlot(
                job_id=job.id,
                hr_id=hr.id,
                start_at=start + timedelta(minutes=30 * k),
                end_at=start + timedelta(minutes=30 * (k + 1)),
                location="Phòng họp tầng 5 / Google Meet",
            )
            for k in range(8)
        ]
        db.add_all(slots)
        db.flush()
        free_slots = iter(slots)
        for (cv, exp), st in zip(rank_cvs_for_job(db, job, k=len(statuses)), statuses):
            app = Application(
                job_id=job.id,
                candidate_id=cv.candidate_id,
                cv_id=cv.id,
                match_score=exp["score"],
                status=st,
                created_at=now() - timedelta(days=rng.randint(1, 10)),
            )
            db.add(app)
            db.flush()
            steps = path[: path.index(st) + 1] if st in path else ["NEW", "SCREENING", "REJECTED"]
            prev = None
            for s in steps:
                db.add(ApplicationHistory(application_id=app.id, from_status=prev, to_status=s, actor_id=hr.id))
                prev = s
            if st in ("INTERVIEW_SCHEDULED", "INTERVIEWED"):
                slot = next(free_slots)
                slot.status, slot.application_id, slot.held_by = "BOOKED", app.id, cv.candidate_id
                if st == "INTERVIEWED":
                    slot.result, slot.feedback = "PASS", "Nền tảng tốt, giao tiếp ổn"
    db.commit()
    print("Đã tạo luồng demo cho hr@demo.vn")


def reembed():
    with SessionLocal() as db:
        embed_all(db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nạp dữ liệu demo; yêu cầu chạy alembic upgrade head trước")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reset", action="store_true", help="Xóa dữ liệu ứng dụng trước khi nạp demo")
    mode.add_argument("--reembed", action="store_true", help="Tính lại vector, giữ nguyên dữ liệu nghiệp vụ")
    args = parser.parse_args()
    if args.reembed:
        reembed()
    else:
        seed(reset=args.reset)
        with engine.connect() as c:
            print(
                "Tổng:",
                {
                    t: c.execute(text(f"select count(*) from {t}")).scalar()
                    for t in ("users", "companies", "jobs", "cvs", "applications", "interview_slots")
                },
            )
