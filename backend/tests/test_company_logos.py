"""Curated avatars fill gaps without replacing employer-owned logos or metadata."""

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core import company_logos
from app.core.database import Base
from app.models import Company, Job, User
from app.services.common import company_out, job_out
from tests.conftest import login, register


@pytest.fixture()
def catalog(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "companies": [
                    {
                        "name": "Công ty Đẹp",
                        "logo_url": "/images/companies/dep.webp",
                        "kind": "recruitment",
                        "source_url": "https://example.vn/employer",
                        "image_url": "https://example.vn/logo.png",
                    },
                    {"name": "Official Company", "logo_url": "/images/companies/official.png", "kind": "official"},
                    {
                        "name": "株式会社 Company",
                        "aliases": ["Company JP", "Company-ジャパン"],
                        "logo_url": "/images/companies/jp.png",
                        "kind": "official",
                    },
                    {"name": "Unknown Company", "logo_url": "/images/companies/unknown.svg", "kind": "placeholder"},
                    {"name": "Bad Path", "logo_url": "/images/companies/../other.svg", "kind": "official"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(company_logos, "CATALOG_PATH", path)
    return path


@pytest.mark.parametrize("name", ["Công ty Đẹp", " CONG   TY DEP ", "công\tTy\nđẹp", "Công ty Đẹp", "Công-Ty.Đẹp"])
def test_catalog_matches_exact_normalized_names(catalog, name):
    assert company_logos.catalog_company_logo_url(name) == "/images/companies/dep.webp"
    assert company_logos.catalog_company_logo_url("Official Company") == "/images/companies/official.png"
    assert company_logos.catalog_company_logo_url("Công ty Đẹp Group") is None
    assert company_logos.catalog_company_logo_url("Unknown Company") is None
    assert company_logos.catalog_company_logo_url("Bad Path") is None


def test_catalog_aliases_keep_unicode_company_names(catalog):
    for name in ("株式会社 Company", "Company JP", "Company ジャパン"):
        assert company_logos.catalog_company_logo_url(name) == "/images/companies/jp.png"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("ＴＥＣＨ - ＣＯ", "tech co"),
        ("Straße GmbH", "straße gmbh"),
        ("Company ジャパン", "company シャハン"),
        ("कंपनी", "कपन"),
    ],
)
def test_normalization_matches_frontend_unicode_rules(name, expected):
    assert company_logos.normalize_company_name(name) == expected


def test_ambiguous_names_do_not_receive_another_company_logo(tmp_path):
    path = tmp_path / "ambiguous.json"
    path.write_text(
        json.dumps(
            {
                "companies": [
                    {"name": "Công ty Đẹp", "logo_url": "/images/companies/first.webp", "kind": "recruitment"},
                    {"name": "CONG TY DEP", "logo_url": "/images/companies/second.webp", "kind": "official"},
                    {"name": "Cong ty dep", "logo_url": "/images/companies/third.webp", "kind": "recruitment"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert company_logos.catalog_company_logo_url("Công ty Đẹp", path) is None


def test_serialization_resolves_missing_logos_without_mutation(catalog):
    company = Company(id=7, name="Công ty Đẹp", status="APPROVED")
    job = Job(id=8, title="Developer", role="software_engineer", company=company)
    assert company_out(company)["logo_url"] == "/images/companies/dep.webp"
    assert job_out(job)["company"]["logo_url"] == "/images/companies/dep.webp"
    assert company.logo_url is None

    company.logo_url = "https://employer.vn/custom-logo.png"
    assert company_out(company)["logo_url"] == company.logo_url
    assert job_out(job)["company"]["logo_url"] == company.logo_url

    company.name, company.logo_url = "An Unlisted Employer", " \t "
    assert company_out(company)["logo_url"] == company_logos.COMPANY_PLACEHOLDER_URL
    assert job_out(job)["company"]["logo_url"] == company_logos.COMPANY_PLACEHOLDER_URL
    assert company.logo_url == " \t "


def test_owner_profile_keeps_editable_logo_blank_and_public_profile_resolves_it(client, catalog):
    hr = register(client, "logo-owner@test.vn", "HR", "Công ty Đẹp")
    owner_profile = client.get("/api/v1/companies/me", headers=hr).json()
    assert owner_profile["logo_url"] is None
    company_id = owner_profile["id"]
    admin = login(client, "admin@t.vn")
    assert (
        client.post(
            f"/api/v1/admin/companies/{company_id}/review",
            json={"status": "APPROVED"},
            headers=admin,
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/companies/{company_id}").json()["logo_url"] == "/images/companies/dep.webp"

    # Saving unrelated profile fields must not turn a display fallback into an upload.
    owner_profile["description"] = "Updated company description"
    saved = client.put("/api/v1/companies/me", headers=hr, json=owner_profile)
    assert saved.status_code == 200
    assert saved.json()["logo_url"] is None
    assert client.get("/api/v1/companies/me", headers=hr).json()["logo_url"] is None
    assert client.get(f"/api/v1/companies/{company_id}").json()["logo_url"] == "/images/companies/dep.webp"

    custom_logo = "https://employer.vn/new-upload.png"
    owner_profile["logo_url"] = custom_logo
    saved = client.put("/api/v1/companies/me", headers=hr, json=owner_profile)
    assert saved.status_code == 200
    assert saved.json()["logo_url"] == custom_logo
    assert client.get(f"/api/v1/companies/{company_id}").json()["logo_url"] == custom_logo


def test_sync_preview_apply_and_repeat_preserve_custom_logos_and_company_data(catalog, tmp_path):
    file = Path(__file__).resolve().parents[1] / "scripts/sync_company_logos.py"
    spec = importlib.util.spec_from_file_location("sync_company_logos", file)
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    engine = create_engine(f"sqlite:///{tmp_path / 'logos_test.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    samples = [
        ("Công ty Đẹp", None),
        ("Official Company", "\t \u2003"),
        ("CONG TY DEP", "https://employer.vn/upload.png"),
        ("An Unlisted Employer", None),
    ]
    with sessions.begin() as db:
        for index, (name, logo) in enumerate(samples):
            db.add(
                Company(
                    owner=User(email=f"hr{index}@test.vn", password_hash="unchanged", full_name="HR", role="HR"),
                    name=name,
                    logo_url=logo,
                    description="Employer description",
                    location="Hà Nội",
                    website="https://employer.vn",
                    status="APPROVED",
                )
            )
    with sessions() as db:
        preview = sync.sync_company_logos(db)
        assert (
            preview["mode"],
            preview["matched"],
            preview["updated"],
            preview["preserved"],
            preview["unmatched"],
        ) == (
            "dry_run",
            2,
            0,
            1,
            1,
        )
        db.commit()
        assert [c.logo_url for c in db.scalars(select(Company).order_by(Company.id))] == [s[1] for s in samples]
        applied = sync.sync_company_logos(db, apply=True)
        assert applied["updated"] == 2
        db.commit()

    with sessions() as db:
        companies = db.scalars(select(Company).order_by(Company.id)).all()
        assert [c.logo_url for c in companies] == [
            "/images/companies/dep.webp",
            "/images/companies/official.png",
            "https://employer.vn/upload.png",
            None,
        ]
        for index, company in enumerate(companies):
            assert company.name == samples[index][0]
            assert (company.description, company.location, company.website, company.status) == (
                "Employer description",
                "Hà Nội",
                "https://employer.vn",
                "APPROVED",
            )
        repeated = sync.sync_company_logos(db, apply=True)
        assert (repeated["matched"], repeated["updated"], repeated["preserved"], repeated["unmatched"]) == (0, 0, 3, 1)
        db.commit()
    engine.dispose()
