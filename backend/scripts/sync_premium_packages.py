"""Apply the candidate Premium catalog without reseeding or touching existing orders.

Run with the backend's configured DATABASE_URL:
    python backend/scripts/sync_premium_packages.py

Orders keep their original amount. Existing package durations and quotas must match
the catalog because activation and refunds read those values from the package.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.package_catalog import CANDIDATE_PREMIUM_PACKAGES  # noqa: E402
from app.models import Package  # noqa: E402


def sync_premium_packages(db: Session) -> dict[str, int]:
    """Update known catalog codes in the caller's transaction; retain package IDs."""
    codes = [item[0] for item in CANDIDATE_PREMIUM_PACKAGES]
    existing = {
        package.code: package
        for package in db.scalars(select(Package).where(Package.code.in_(codes)).with_for_update())
    }
    # Validate every existing row before changing any catalog fields. Historical
    # orders/subscriptions have no separate benefit snapshot, so keep benefits stable.
    for code, _, target, _, days, quota, _ in CANDIDATE_PREMIUM_PACKAGES:
        package = existing.get(code)
        if package and (package.target, package.duration_days, package.quota_jobs) != (target, days, quota):
            raise ValueError(f"{code}: target/duration/quota differ; refusing to change historical order benefits")

    result = {"created": 0, "updated": 0, "unchanged": 0}
    for code, name, target, price, days, quota, description in CANDIDATE_PREMIUM_PACKAGES:
        package = existing.get(code)
        if package is None:
            db.add(
                Package(
                    code=code,
                    name=name,
                    target=target,
                    price=price,
                    duration_days=days,
                    quota_jobs=quota,
                    description=description,
                    active=True,
                )
            )
            result["created"] += 1
        else:
            fields = {"name": name, "price": price, "description": description, "active": True}
            if any(getattr(package, field) != value for field, value in fields.items()):
                for field, value in fields.items():
                    setattr(package, field, value)
                result["updated"] += 1
            else:
                result["unchanged"] += 1
    db.flush()
    return result


def main() -> None:
    with SessionLocal.begin() as db:
        result = sync_premium_packages(db)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
