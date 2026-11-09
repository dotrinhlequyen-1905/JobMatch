from sqlalchemy import func, select, update

from ..core.clock import now
from ..models import Order, PaymentTransaction, Subscription


def find_pending(db, package, user):
    return db.scalar(
        select(Order).where(
            Order.user_id == user.id,
            Order.package_id == package.id,
            Order.status == "PENDING",
            Order.expires_at > now(),
        )
    )


def add_order(db, order):
    return db.add(order)


def add_subscription(db, order, pkg, interval, start):
    return db.add(
        Subscription(
            user_id=order.user_id,
            package_id=pkg.id,
            order_id=order.id,
            starts_at=start,
            ends_at=start + interval,
            remaining_quota=pkg.quota_jobs,
        )
    )


def add_transaction(db, tx):
    return db.add(tx)


def lock_order(db, m):
    return db.get(Order, int(m.group(1)), with_for_update=True)


def mark_paid(db, order):
    return db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status.in_(["PENDING", "RECONCILING"]))
        .values(status="PAID", paid_at=now())
        .execution_options(synchronize_session=False)
    )


def expire_pending(db):
    return db.execute(
        update(Order)
        .where(Order.status == "PENDING", Order.expires_at < now())
        .values(status="EXPIRED")
        .execution_options(synchronize_session=False)
    )


def paid_orders(db):
    return db.scalars(select(Order).where(Order.status.in_(["PAID", "REFUND_REQUESTED", "REFUNDED"]))).all()


def matched_transactions(db):
    """Giao dịch đã được chấp nhận cho đơn: khớp tự động hoặc quản trị viên duyệt khi đối soát."""
    return db.scalars(select(PaymentTransaction).where(PaymentTransaction.status.in_(["MATCHED", "RESOLVED"])))


def unmatched_transactions(db):
    return db.scalars(
        select(PaymentTransaction).where(
            PaymentTransaction.status.in_(["UNMATCHED", "LATE", "AMOUNT_MISMATCH", "REFUND_DUE"])
        )
    ).all()


def total_received(db):
    return db.scalar(select(func.coalesce(func.sum(PaymentTransaction.amount), 0)))


def stuck_orders(db):
    return db.scalar(select(func.count()).select_from(Order).where(Order.status == "PENDING", Order.expires_at < now()))


def subscription_for_refund(db, order):
    return db.scalar(select(Subscription).where(Subscription.order_id == order.id))


def request_refund(db, order):
    return db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == "PAID")
        .values(status="REFUND_REQUESTED")
        .execution_options(synchronize_session=False)
    )


def add_refund(db, refund):
    return db.add(refund)


def subscription_for_reversal(db, order):
    return db.scalar(select(Subscription).where(Subscription.order_id == order.id))


def active_hr_subscription(db, user_id):
    return db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.active.is_(True),
            Subscription.ends_at > now(),
            Subscription.remaining_quota > 0,
        )
        .order_by(Subscription.ends_at)
        .with_for_update()
    )


def mark_reconciling(db, order):
    return db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status.in_(["PENDING", "EXPIRED"]))
        .values(status="RECONCILING")
        .execution_options(synchronize_session=False)
    )


def reconciling_count(db):
    return db.scalar(select(func.count()).select_from(Order).where(Order.status == "RECONCILING"))


def known_transaction_ids(db, ids):
    return set(db.scalars(select(PaymentTransaction.sepay_tx_id).where(PaymentTransaction.sepay_tx_id.in_(ids))))


def lock_order_by_id(db, order_id):
    return db.get(Order, order_id, with_for_update=True)


def find_order_by_code(db, code):
    return db.scalar(select(Order).where(func.upper(Order.order_code) == code.strip().upper()).with_for_update())


def lock_transaction(db, tx_id):
    return db.get(PaymentTransaction, tx_id, with_for_update=True)


def open_transactions_for_order(db, order):
    return db.scalars(
        select(PaymentTransaction).where(
            PaymentTransaction.order_id == order.id, PaymentTransaction.status != "MATCHED"
        )
    ).all()
