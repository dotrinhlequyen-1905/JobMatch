"""Catalog repricing must preserve historical payment amounts and purchased benefits."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import Order, Package, Subscription, User
from app.services.common import aware, now
from app.services.payments import create_order, handle_webhook
from scripts.sync_premium_packages import sync_premium_packages


@pytest.fixture()
def catalog_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'premium_test.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        user = User(email="premium@test.vn", password_hash="unused", full_name="Candidate", role="CANDIDATE")
        month = Package(
            code="CAND_PREMIUM_30", name="Old month", target="CANDIDATE", price=49000, duration_days=30
        )
        quarter = Package(
            code="CAND_PREMIUM_90", name="Old quarter", target="CANDIDATE", price=119000, duration_days=90
        )
        hr = Package(
            code="HR_BASIC", name="HR unchanged", target="HR", price=199000, duration_days=30, quota_jobs=5
        )
        db.add_all([user, month, quarter, hr])
        db.flush()
        pending = Order(
            user_id=user.id,
            package_id=month.id,
            amount=49000,
            status="PENDING",
            expires_at=now() + timedelta(minutes=15),
        )
        paid = Order(
            user_id=user.id,
            package_id=quarter.id,
            amount=119000,
            status="PAID",
            expires_at=now() + timedelta(minutes=15),
            paid_at=now(),
        )
        db.add_all([pending, paid])
        db.flush()
        pending.order_code = f"QTD{pending.id:06d}"
        paid.order_code = f"QTD{paid.id:06d}"
        user.premium_until = now() + timedelta(days=90)
        db.add(
            Subscription(
                user_id=user.id,
                package_id=quarter.id,
                order_id=paid.id,
                starts_at=now(),
                ends_at=user.premium_until,
            )
        )
        db.commit()
        yield db, user, pending, paid
    engine.dispose()


def test_sync_is_idempotent_and_preserves_historical_orders(catalog_db):
    db, user, pending, paid = catalog_db
    original_ids = (pending.package_id, paid.package_id)
    original_until = aware(user.premium_until)
    original_subscription = db.scalar(select(Subscription))
    original_ends_at = aware(original_subscription.ends_at)

    assert sync_premium_packages(db) == {"created": 1, "updated": 2, "unchanged": 0}
    db.commit()
    assert sync_premium_packages(db) == {"created": 0, "updated": 0, "unchanged": 3}
    db.commit()
    db.expire_all()

    assert (pending.package_id, paid.package_id) == original_ids
    assert (pending.amount, pending.status) == (49000, "PENDING")
    assert (paid.amount, paid.status) == (119000, "PAID")
    assert aware(user.premium_until) == original_until
    assert aware(original_subscription.ends_at) == original_ends_at
    candidates = db.scalars(select(Package).where(Package.target == "CANDIDATE").order_by(Package.duration_days)).all()
    assert [(package.price, package.duration_days) for package in candidates] == [(99000, 30), (249000, 90), (899000, 365)]
    assert [package.id for package in candidates[:2]] == list(original_ids)
    hr = db.scalar(select(Package).where(Package.code == "HR_BASIC"))
    assert (hr.name, hr.price, hr.duration_days, hr.quota_jobs) == ("HR unchanged", 199000, 30, 5)


def test_old_price_still_settles_and_new_orders_use_new_catalog(catalog_db):
    db, user, pending, _ = catalog_db
    previous_until = aware(user.premium_until)
    sync_premium_packages(db)
    db.commit()

    # The existing pending order is honored at its original price after repricing.
    assert handle_webhook(
        db, {"id": "old-price", "transferAmount": 49000, "content": pending.order_code, "transferType": "in"}
    )["status"] == "MATCHED"
    assert pending.status == "PAID"
    assert pending.amount == 49000
    assert aware(user.premium_until) == previous_until + timedelta(days=30)

    fresh_month = create_order(db, user, pending.package)
    assert fresh_month.id != pending.id
    assert fresh_month.amount == 99000
    year = db.scalar(select(Package).where(Package.code == "CAND_PREMIUM_365"))
    fresh_year = create_order(db, user, year)
    assert fresh_year.amount == 899000
    db.commit()
    assert handle_webhook(
        db, {"id": "new-year", "transferAmount": 899000, "content": fresh_year.order_code, "transferType": "in"}
    )["status"] == "MATCHED"
    assert aware(user.premium_until) == previous_until + timedelta(days=30 + 365)
    subscription = db.scalar(select(Subscription).where(Subscription.order_id == fresh_year.id))
    assert aware(subscription.ends_at) - aware(subscription.starts_at) == timedelta(days=365)


def test_sync_refuses_to_change_historical_duration_before_any_writes(catalog_db):
    db, _, pending, paid = catalog_db
    paid.package.duration_days = 80
    db.commit()
    with pytest.raises(ValueError, match="historical order benefits"):
        sync_premium_packages(db)
    db.rollback()
    assert pending.package.price == 49000
    assert paid.package.price == 119000
    assert db.scalar(select(Package).where(Package.code == "CAND_PREMIUM_365")) is None
