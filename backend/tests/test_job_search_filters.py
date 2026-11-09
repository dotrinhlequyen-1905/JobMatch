"""Public jobs filters against a fresh, isolated in-memory SQLite database."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.jobs import router
from app.core.database import Base, get_db
from app.models import Company, Job, User


@pytest.fixture()
def job_search_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(email="filters@example.test", full_name="Owner", password_hash="unused", role="HR")
        db.add(owner)
        db.flush()
        company = Company(owner_id=owner.id, name="Filter Company", status="APPROVED")
        db.add(company)
        db.commit()
        company_id = company.id

    def seed(*jobs):
        ids = []
        with Session(engine) as db:
            for values in jobs:
                defaults = {
                    "company_id": company_id,
                    "title": "Python Developer",
                    "description": "Build services",
                    "role": "backend",
                    "seniority": "junior",
                    "skills": ["Python"],
                    "city": "Hà Nội",
                    "min_years": 2,
                    "salary_min": 12_000_000,
                    "salary_max": 20_000_000,
                    "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "status": "PUBLISHED",
                }
                job = Job(**(defaults | values))
                db.add(job)
                db.flush()
                ids.append(job.id)
            db.commit()
        return ids

    def isolated_db():
        with Session(engine) as db:
            yield db

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = isolated_db
    try:
        with TestClient(app) as client:
            yield client, seed, company_id
    finally:
        engine.dispose()


def test_multiselect_filters_combine_with_legacy_filters(job_search_client):
    client, seed, company_id = job_search_client
    ids = seed(
        {},
        {"city": "Hồ Chí Minh", "min_years": 4},
        {"city": "Remote"},
        {"city": "Làm từ xa", "min_years": 4},
        {"city": "Làm việc từ xa", "min_years": 1},
        {"city": None},
        {"min_years": 0},
        {"salary_min": 26_000_000, "salary_max": 30_000_000},
        {"status": "CLOSED"},
        {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)},
        {"title": "Designer", "skills": ["Design"], "role": "design"},
        {"seniority": "senior"},
    )
    legacy = {
        "q": "Developer",
        "city": "Hà Nội",
        "role": "backend",
        "seniority": "junior",
        "skill": "Python",
        "company_id": str(company_id),
    }
    response = client.get(
        "/api/v1/jobs",
        params=list(legacy.items())
        + [
            ("cities", "Remote"),
            ("experience", "1_3"),
            ("experience", "3_5"),
            ("salary_range", "15_25"),
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 4
    assert {item["id"] for item in response.json()["items"]} == {ids[0], ids[2], ids[3], ids[4]}

    response = client.get("/api/v1/jobs", params=legacy)
    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {ids[0], ids[6], ids[7]}

    response = client.get("/api/v1/jobs", params=[("cities", "Hà Nội"), ("cities", "Hồ Chí Minh")])
    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {ids[index] for index in (0, 1, 6, 7, 10, 11)}


def test_keyword_matches_skills_without_matching_title_description_or_company(job_search_client):
    client, seed, _ = job_search_client
    ids = seed(
        {"skills": ["Docker"]},
        {"skills": ["Python"]},
        {"skills": ["Docker"], "city": "Hồ Chí Minh"},
        {"skills": ["Docker"], "status": "CLOSED"},
    )
    response = client.get("/api/v1/jobs", params={"q": "docker"})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert {item["id"] for item in response.json()["items"]} == {ids[0], ids[2]}

    response = client.get(
        "/api/v1/jobs",
        params={"q": "docker", "cities": "Hà Nội", "salary_range": "10_15", "experience": "1_3"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [ids[0]]


@pytest.mark.parametrize(
    "salary_range, expected",
    [
        ("under_10", {0, 4, 6}),
        ("10_15", {1, 4, 6}),
        ("15_25", {2, 4, 5}),
        ("over_25", {3, 5}),
    ],
)
def test_salary_interval_overlap_boundaries_and_missing_endpoints(job_search_client, salary_range, expected):
    client, seed, _ = job_search_client
    salaries = [(8, 8), (10, 10), (15, 15), (25, 25), (9, 16), (20, None), (None, 12), (None, None)]
    ids = seed(
        *(
            {
                "salary_min": low * 1_000_000 if low is not None else None,
                "salary_max": high * 1_000_000 if high is not None else None,
            }
            for low, high in salaries
        )
    )
    response = client.get("/api/v1/jobs", params={"salary_range": salary_range})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == len(expected)
    assert {item["id"] for item in response.json()["items"]} == {ids[index] for index in expected}


@pytest.mark.parametrize(
    "experience, expected",
    [
        ("none", {0}),
        ("under_1", {0}),
        ("1_3", {1, 2}),
        ("3_5", {3, 4}),
        ("over_5", {5, 6}),
    ],
)
def test_experience_integer_boundaries(job_search_client, experience, expected):
    client, seed, _ = job_search_client
    ids = seed(*({"min_years": years} for years in range(7)))
    response = client.get("/api/v1/jobs", params={"experience": experience})
    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {ids[index] for index in expected}


@pytest.mark.parametrize(
    "sort, expected",
    [
        (None, [2, 1, 3, 0]),
        ("newest", [2, 1, 3, 0]),
        ("oldest", [0, 3, 1, 2]),
        ("salary_desc", [2, 1, 0, 3]),
    ],
)
def test_sorting_is_stable_across_pages(job_search_client, sort, expected):
    client, seed, _ = job_search_client
    ids = seed(
        {"salary_min": 8_000_000, "salary_max": 8_000_000},
        {"salary_max": 30_000_000, "created_at": datetime(2024, 1, 3, tzinfo=timezone.utc)},
        {"salary_min": 30_000_000, "salary_max": None, "created_at": datetime(2024, 1, 3, tzinfo=timezone.utc)},
        {"salary_min": None, "salary_max": None, "created_at": datetime(2024, 1, 2, tzinfo=timezone.utc)},
    )
    found = []
    for page in (1, 2):
        params = {"page": page, "size": 2}
        if sort:
            params["sort"] = sort
        response = client.get("/api/v1/jobs", params=params)
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 4
        assert response.json()["page"] == page
        assert response.json()["size"] == 2
        found.extend(item["id"] for item in response.json()["items"])
    assert found == [ids[index] for index in expected]


@pytest.mark.parametrize(
    "params",
    [
        {"salary_range": "invalid"},
        {"experience": "invalid"},
        {"sort": "invalid"},
        [("experience", "none"), ("experience", "invalid")],
    ],
)
def test_unknown_filter_values_are_rejected(job_search_client, params):
    client, _, _ = job_search_client
    response = client.get("/api/v1/jobs", params=params)
    assert response.status_code == 422
