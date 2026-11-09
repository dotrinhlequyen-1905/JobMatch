"""Seeder must work with the new matcher and never erase an existing database by default."""

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core import company_logos
from app.models import CV, Application, Company, InterviewSlot, User


def test_demo_seed_and_existing_data_guard(tmp_path, monkeypatch):
    file = Path(__file__).resolve().parents[1] / "scripts/seed.py"
    spec = importlib.util.spec_from_file_location("demo_seed", file)
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    engine = create_engine(f"sqlite:///{tmp_path / 'seed_test.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", sessions)
    job = {
        "company": "Demo Company",
        "city": "Hà Nội",
        "title": "Python Developer",
        "description": "Python, FastAPI, PostgreSQL, Docker; yêu cầu hai năm kinh nghiệm.",
        "role": "software_engineer",
        "seniority": "junior",
        "min_years": 2,
        "skills": ["Python", "PostgreSQL", "Docker"],
    }
    candidates = [
        {
            "name": f"Candidate {index}",
            "phone": "0912345678",
            "email": f"candidate{index}@example.vn",
            "title": "Python Developer",
            "text": "Python, PostgreSQL, Docker",
            "summary": "Python developer",
            "experience": [{"position": "Developer", "start": "2022", "end": None}],
            "education": {"major": "Computer Science"},
            "years": 4,
            "seniority": "junior",
            "role": "software_engineer",
            "skills": ["Python", "PostgreSQL", "Docker"],
        }
        for index in range(8)
    ]
    samples = {"jobs.jsonl": [job], "cvs.jsonl": candidates}
    monkeypatch.setattr(seed, "load", lambda name: samples[name])
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"companies": [
        {"name": "Demo Company", "logo_url": "/images/companies/demo.webp", "kind": "recruitment"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(company_logos, "CATALOG_PATH", catalog_path)
    seed.seed()
    with sessions() as db:
        assert db.scalar(select(Company.logo_url)) == "/images/companies/demo.webp"
        assert db.scalar(select(func.count(CV.id))) == 8
        assert db.scalar(select(func.count(Application.id))) == 8
        assert db.scalar(select(func.count(InterviewSlot.id))) == 8
        candidate = db.scalar(select(User).where(User.email == "candidate@demo.vn"))
        original_id = candidate.id
    with pytest.raises(SystemExit, match="DB đã có dữ liệu"):
        seed.seed()
    with sessions() as db:
        assert db.scalar(select(User.id).where(User.email == "candidate@demo.vn")) == original_id
        assert db.scalar(select(func.count(Application.id))) == 8
    engine.dispose()
