"""Cache employer avatars from the original recruitment dataset.

Run from the repository root with ``uv run --with pillow scripts/import_company_logos.py``.
Existing verified catalog entries are reused; official overrides are preserved.
The importer keeps source URLs, rejects known platform placeholders, validates
images, and stores bounded WebP files for predictable, offline frontend loading.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "frontend/public/images/companies"
CATALOG = DEST / "catalog.json"
MAX_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; EmployerLogoImporter/1.0)"
TECHPLUS = "CÔNG TY TRÁCH NHIỆM HỮU HẠN GIẢI PHÁP CÔNG NGHỆ CỘNG"
ITVIEC_INTERVAL = 1.0
_itviec_lock = threading.Lock()
_itviec_next_request = 0.0


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    plain = "".join(ch for ch in decomposed if not unicodedata.category(ch).startswith("M")).replace("đ", "d")
    return " ".join("".join(ch if ch.isalnum() else " " for ch in plain).split())


def fetch(url: str, *, html: bool = False) -> bytes:
    global _itviec_next_request
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("invalid public source URL")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        if parsed.hostname == "itviec.com":
            with _itviec_lock:
                delay = max(0, _itviec_next_request - time.monotonic())
                if delay:
                    time.sleep(delay)
                _itviec_next_request = time.monotonic() + ITVIEC_INTERVAL
        try:
            with urllib.request.urlopen(request, timeout=22) as response:
                content_type = response.headers.get("Content-Type", "").casefold()
                if not html and ("text/html" in content_type or "application/json" in content_type):
                    raise ValueError("source returned a page rather than an image")
                data = response.read(MAX_BYTES + 1)
            break
        except HTTPError as exc:
            if parsed.hostname != "itviec.com" or exc.code != 429 or attempt == 2:
                raise
            with _itviec_lock:
                try:
                    retry_after = float(exc.headers.get("Retry-After", "60"))
                except ValueError:
                    retry_after = 60
                _itviec_next_request = max(_itviec_next_request, time.monotonic() + min(120, max(30, retry_after)))
    if len(data) > MAX_BYTES:
        raise ValueError("source exceeds image size limit")
    return data


def is_placeholder(url: str) -> bool:
    lowered = url.casefold()
    return any(part in lowered for part in ("logo_default", "default_company", "company-default", "static.licdn.com/"))


def store_image(data: bytes) -> str:
    try:
        with Image.open(io.BytesIO(data)) as candidate:
            candidate.verify()
        with Image.open(io.BytesIO(data)) as candidate:
            if min(candidate.size) < 16 or max(candidate.size) > 16000:
                raise ValueError("image dimensions indicate a tracker or unsupported asset")
            image = ImageOps.exif_transpose(candidate).convert("RGBA")
            image.thumbnail((320, 320), Image.Resampling.LANCZOS)
            if image.getbbox() is None or len(image.getcolors(image.width * image.height) or []) < 2:
                raise ValueError("empty or single-color image")
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=95, method=6)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("invalid raster image") from exc
    encoded = output.getvalue()
    filename = hashlib.sha256(encoded).hexdigest()[:20] + ".webp"
    (DEST / filename).write_bytes(encoded)
    return "/images/companies/" + filename


class ProfileMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.metadata: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        fields = dict(attrs)
        key = fields.get("property") or fields.get("name")
        if key and fields.get("content"):
            self.metadata[key] = fields["content"] or ""


def current_itviec_logo(name: str) -> tuple[str, str]:
    # Rails signed URLs in the research snapshot expired after an ITviec upgrade.
    # Only accept the replacement logo when the current employer page identifies
    # the same normalized company, never an unrelated search result.
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_name(name)).strip("-")
    page_url = "https://itviec.com/companies/" + slug
    parser = ProfileMetadata()
    parser.feed(fetch(page_url, html=True).decode("utf-8", errors="replace"))
    title = normalize_name(parser.metadata.get("og:title", ""))
    name_words = re.sub(r"[^a-z0-9]+", " ", normalize_name(name)).strip()
    title_words = re.sub(r"[^a-z0-9]+", " ", title).strip()
    image_url = parser.metadata.get("og:image", "")
    if name_words not in title_words or not image_url or "active_storage" not in image_url:
        raise ValueError("current employer profile identity could not be verified")
    return image_url, page_url


def source_candidates(row: dict[str, str]) -> list[str]:
    original = row["company_image_url"].strip()
    if "itviec.com/rails/active_storage/" in original and "eyJfcmFpbHMiOnsibWVzc2FnZSI6" in original:
        return []  # The old Rails message signatures are no longer accepted.
    candidates = []
    if "cdn-new.topcv.vn/unsafe/" in original and "/https://" in original:
        candidates.append("https://" + original.split("/https://", 1)[1])
    candidates.append(original)
    return list(dict.fromkeys(candidates))


def covered_names(imported: dict[str, dict]) -> set[str]:
    covered = set(imported)
    for entry in imported.values():
        for alias in entry.get("aliases", []):
            if isinstance(alias, str):
                covered.add(normalize_name(alias))
    return covered


def import_one(name: str, rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, str]:
    errors = []
    tried: set[str] = set()
    for row in sorted(rows, key=lambda item: {"TopCV": 0, "LinkedIn": 1, "ITViec": 2}.get(item["site"], 3)):
        for image_url in source_candidates(row):
            if image_url in tried or is_placeholder(image_url):
                continue
            tried.add(image_url)
            try:
                logo_url = store_image(fetch(image_url))
                return {"name": name, "logo_url": logo_url, "source_url": row["job_url"], "image_url": image_url, "kind": "recruitment"}, ""
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
    if any(row["site"] == "ITViec" for row in rows):
        try:
            image_url, page_url = current_itviec_logo(name)
            logo_url = store_image(fetch(image_url))
            return {"name": name, "logo_url": logo_url, "source_url": page_url, "image_url": image_url, "kind": "recruitment"}, ""
        except Exception as exc:
            errors.append(f"profile recovery: {type(exc).__name__}: {exc}")
    return None, errors[-1] if errors else "original recruitment source uses a platform placeholder"


def apply_curated_entries(imported: dict[str, dict]) -> None:
    """Keep official artwork and reviewed same-company matches above imported images."""
    if (DEST / "techplus-official.webp").is_file():
        imported[normalize_name(TECHPLUS)] = {
            "name": TECHPLUS,
            "logo_url": "/images/companies/techplus-official.webp",
            "source_url": "https://vi.techplus.vn/",
            "image_url": "https://vi.techplus.vn/wp-content/uploads/sites/2/2020/11/cropped-favicon-1-192x192.png",
            "kind": "official",
            "aliases": ["TechPlus", "TechPlus Solution"],
        }
    overrides_path = ROOT / ".cache/company-avatars/official-overrides.json"
    if overrides_path.is_file():
        for entry in json.loads(overrides_path.read_text(encoding="utf-8")):
            local_path = ROOT / "frontend/public" / entry.get("logo_url", "").lstrip("/")
            if entry.get("kind") == "official" and entry.get("name") and local_path.is_file():
                imported[normalize_name(entry["name"])] = entry
    associations_path = ROOT / ".cache/company-avatar-associations.json"
    if associations_path.is_file():
        for association in json.loads(associations_path.read_text(encoding="utf-8")):
            target_key = normalize_name(association["name"])
            source_entry = imported.get(normalize_name(association["existing_name"]))
            if target_key in imported or not source_entry:
                continue
            entry = dict(source_entry)
            entry.pop("aliases", None)
            entry["name"] = association["name"]
            entry["association_source_url"] = association["source_url"]
            imported[target_key] = entry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--limit", type=int, help="Limit missing companies, for a source smoke check")
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    original_names = {json.loads(line)["company"] for line in (ROOT / "data/final/jobs.jsonl").open(encoding="utf-8")}
    names: dict[str, str] = {}
    for name in sorted(original_names):
        names.setdefault(normalize_name(name), name.strip())
    raw: dict[str, list[dict[str, str]]] = defaultdict(list)
    with (ROOT / "data/raw/IT-Job-Posting/job_descriptions.csv").open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            raw[normalize_name(row["company"])].append(row)
    existing = json.loads(CATALOG.read_text(encoding="utf-8")).get("companies", []) if CATALOG.exists() else []
    imported = {}
    for entry in existing:
        path = ROOT / "frontend/public" / entry.get("logo_url", "").lstrip("/")
        if path.is_file():
            key = normalize_name(entry["name"])
            if key not in imported or entry.get("kind") == "official":
                imported[key] = entry
    existing_coverage = covered_names(imported)
    missing = [(key, name) for key, name in names.items() if key not in existing_coverage]
    if args.limit:
        missing = missing[:args.limit]
    failures = []
    successful = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as workers:
        work = {workers.submit(import_one, name, raw.get(key, [])): (key, name) for key, name in missing}
        for completed, future in enumerate(as_completed(work), 1):
            key, name = work[future]
            entry, error = future.result()
            if entry:
                imported[key] = entry
                successful += 1
            else:
                failures.append({"name": name, "reason": error})
            if completed % 25 == 0 or completed == len(work):
                print(f"Processed {completed}/{len(work)}; cached {len(imported)} company logos; failed {len(failures)}", flush=True)
            if completed % 50 == 0 or (entry and successful % 25 == 0):
                CATALOG.write_text(json.dumps({"version": 1, "companies": sorted(imported.values(), key=lambda item: normalize_name(item["name"]))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    apply_curated_entries(imported)
    final_coverage = covered_names(imported)
    failures = [item for item in failures if normalize_name(item["name"]) not in final_coverage]
    catalog = {
        "version": 1,
        "description": "Locally cached employer logos, verified from their original recruitment images or official website. Platform placeholder images are excluded.",
        "companies": sorted(imported.values(), key=lambda item: normalize_name(item["name"])),
    }
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"dataset_names": len(original_names), "normalized_companies": len(names), "cached_companies": sum(key in final_coverage for key in names), "missing": sorted(failures, key=lambda item: normalize_name(item["name"]))}
    (DEST / "import-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "missing"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
