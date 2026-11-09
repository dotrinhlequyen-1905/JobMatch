"""Fill empty company logo URLs from the curated catalog; retain employer edits.

Preview (default, no writes):
    python backend/scripts/sync_company_logos.py
Apply only the listed empty-logo matches, without reseeding:
    python backend/scripts/sync_company_logos.py --apply
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.company_logos import company_logo_catalog, normalize_company_name  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Company  # noqa: E402


def sync_company_logos(db: Session, *, apply: bool = False, catalog_path: Path | None = None) -> dict:
    """Change only blank logo fields in the caller's transaction, never metadata."""
    catalog = company_logo_catalog(catalog_path)
    result = {
        "mode": "apply" if apply else "dry_run",
        "matched": 0,
        "updated": 0,
        "preserved": 0,
        "unmatched": 0,
        "changes": [],
    }
    rows = db.execute(select(Company.id, Company.name, Company.logo_url).order_by(Company.id)).all()
    for company_id, name, original_logo_url in rows:
        if original_logo_url and original_logo_url.strip():
            result["preserved"] += 1
            continue
        logo_url = catalog.get(normalize_company_name(name))
        if not logo_url:
            result["unmatched"] += 1
            continue
        result["matched"] += 1
        result["changes"].append({"id": company_id, "name": name, "logo_url": logo_url})
        if apply:
            # An employer may upload a logo after the preview/select. Compare the
            # original blank value again so this update cannot replace that upload.
            original_value = (
                Company.logo_url.is_(None) if original_logo_url is None else Company.logo_url == original_logo_url
            )
            changed = db.execute(
                update(Company).where(Company.id == company_id, original_value).values(logo_url=logo_url)
            )
            result["updated"] += changed.rowcount
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill empty employer logos; dry run unless --apply is supplied")
    parser.add_argument("--apply", action="store_true", help="Save matched logos without changing existing logos")
    parser.add_argument("--catalog", type=Path, help="Use a catalog JSON file from another deployment location")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = sync_company_logos(db, apply=args.apply, catalog_path=args.catalog)
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
