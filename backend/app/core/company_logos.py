"""Resolve curated employer avatars without changing company-owned logo URLs."""

import json
import logging
import unicodedata
from functools import lru_cache
from pathlib import Path, PurePosixPath

from ..config import ROOT_DIR

CATALOG_PATH = ROOT_DIR / "frontend/public/images/companies/catalog.json"
COMPANY_PLACEHOLDER_URL = "/images/companies/company-placeholder.svg"
CATALOG_KINDS = {"official", "recruitment"}


def normalize_company_name(name: str | None) -> str:
    """Match names across accents, case, punctuation and whitespace variants."""
    name = unicodedata.normalize("NFKD", (name or "").lower())
    name = "".join(char for char in name if not unicodedata.category(char).startswith("M")).replace("đ", "d")
    name = "".join(char if char.isalnum() else " " for char in name)
    return " ".join(name.split())


@lru_cache(maxsize=4)
def _read_catalog(path: Path, modified_at: int) -> dict[str, str]:
    # The modification timestamp is part of the cache key so a refreshed catalog
    # is picked up without restarting a local development server.
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        logging.getLogger(__name__).warning("Cannot read company logo catalog at %s", path)
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("companies"), list):
        return {}

    logos, ambiguous = {}, set()
    for item in payload["companies"]:
        if not isinstance(item, dict) or not isinstance(item.get("kind"), str) or item["kind"] not in CATALOG_KINDS:
            continue
        name, logo_url = item.get("name"), item.get("logo_url")
        if not isinstance(name, str) or not isinstance(logo_url, str):
            continue
        if (
            not logo_url.startswith("/images/companies/")
            or ".." in PurePosixPath(logo_url).parts
            or any(char in logo_url for char in ("\\", "?", "#"))
        ):
            continue
        aliases = item.get("aliases", [])
        names = [name, *(alias for alias in aliases if isinstance(alias, str))] if isinstance(aliases, list) else [name]
        for company_name in names:
            key = normalize_company_name(company_name)
            if not key or key in ambiguous:
                continue
            if key in logos and logos[key] != logo_url:
                # Avoid silently assigning another company's logo when names collide.
                logos.pop(key)
                ambiguous.add(key)
            else:
                logos[key] = logo_url
    return logos


def company_logo_catalog(catalog_path: Path | None = None) -> dict[str, str]:
    path = catalog_path or CATALOG_PATH
    try:
        modified_at = path.stat().st_mtime_ns
    except OSError:
        return {}
    return _read_catalog(path, modified_at)


def catalog_company_logo_url(name: str | None, catalog_path: Path | None = None) -> str | None:
    return company_logo_catalog(catalog_path).get(normalize_company_name(name))


def resolve_company_logo_url(name: str | None, logo_url: str | None = None) -> str:
    if logo_url and logo_url.strip():
        return logo_url
    return catalog_company_logo_url(name) or COMPANY_PLACEHOLDER_URL
