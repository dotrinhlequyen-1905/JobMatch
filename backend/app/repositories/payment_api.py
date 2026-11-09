from sqlalchemy import select, update

from ..core.clock import now
from ..models import Order, Package, Refund, User


def active_packages():
    return select(Package).where(Package.active.is_(True)).order_by(Package.price)


def filter_package_target(stmt, target):
    return stmt.where(Package.target == target)


def list_packages(db, stmt):
    return db.scalars(stmt)


def get_package(db, body):
    return db.get(Package, body.package_id)


def list_orders(db, user):
    return db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()


def refunds_for_orders(db, orders):
    return db.scalars(select(Refund).where(Refund.order_id.in_([o.id for o in orders])))


def get_order(db, order_id):
    return db.get(Order, order_id)


def refund_for_order(db, o):
    return db.scalar(select(Refund).where(Refund.order_id == o.id))


def get_order_for_cancel(db, order_id):
    return db.get(Order, order_id)


def get_order_for_refund(db, order_id):
    return db.get(Order, order_id)


def get_order_for_simulation(db, body):
    return db.get(Order, body.order_id)


def get_order_for_demo_payment(db, order_id):
    return db.scalar(
        select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True)
    )


def lock_premium_user(db, user_id):
    return db.get(User, user_id, with_for_update=True, populate_existing=True)


def expire_pending_order(db, order):
    return db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == "PENDING", Order.expires_at <= now())
        .values(status="EXPIRED")
        .execution_options(synchronize_session=False)
    )
