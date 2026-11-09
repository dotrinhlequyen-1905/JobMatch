"""API thanh toán: tạo đơn + VietQR SePay, webhook SePay, yêu cầu hoàn tiền, giả lập webhook (demo/dev)."""

import uuid

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from ..repositories import payment_api as queries
from ..schemas.payments import DemoPaymentIn, OrderIn, RefundIn, SimulateIn
from ..services.common import aware, now, order_out, package_out
from ..services.payments import create_order, handle_webhook, request_refund


def order_detail(order, refund=None):
    return {
        **order_out(order, refund),
        "payment_demo_enabled": settings.payment_demo_enabled,
        "payment_simulation_enabled": settings.enable_dev_tools,
        "bank": {"bank": settings.sepay_bank, "account": settings.sepay_account, "name": settings.sepay_account_name},
    }


def packages(*, target: str | None = None, db: Session):
    stmt = queries.active_packages()
    if target:
        stmt = queries.filter_package_target(stmt, target)
    return [package_out(p) for p in queries.list_packages(db, stmt)]


def new_order(*, body: OrderIn, user: User, db: Session):
    pkg = queries.get_package(db, body)
    if not pkg:
        raise HTTPException(404, "Không tìm thấy gói")
    order = create_order(db, user, pkg)
    db.commit()
    return order_detail(order)


def my_orders(*, user: User, db: Session):
    orders = queries.list_orders(db, user)
    refunds = {r.order_id: r for r in queries.refunds_for_orders(db, orders)}
    return [order_out(o, refunds.get(o.id)) for o in orders]


def get_order(*, order_id: int, user: User, db: Session):
    o = queries.get_order(db, order_id)
    if not o or (o.user_id != user.id and user.role != "ADMIN"):
        raise HTTPException(404, "Không tìm thấy đơn")
    if o.status == "PENDING" and aware(o.expires_at) <= now():
        # Không chờ Celery beat: đơn quá hạn được chốt "Hết hạn" ngay khi người dùng xem.
        queries.expire_pending_order(db, o)
        db.commit()
        db.refresh(o)
    refund = queries.refund_for_order(db, o)
    return order_detail(o, refund)


def demo_payment(*, order_id: int, body: DemoPaymentIn, user: User, db: Session):
    """Chế độ demo: thay cho việc quét QR và chuyển khoản thật, tạo webhook đúng định dạng SePay
    rồi đưa qua chính `handle_webhook` (idempotent, đối chiếu mã đơn + số tiền, kích hoạt gói)."""
    if not settings.payment_demo_enabled:
        raise HTTPException(404, "Thanh toán demo chưa được bật")
    o = queries.get_order_for_demo_payment(db, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn")
    if o.status == "PAID":
        return order_detail(o)
    if o.status != "PENDING":
        raise HTTPException(409, "Chỉ giả lập thanh toán cho đơn đang chờ thanh toán")
    # Tuần tự hóa các lần gia hạn của cùng người dùng, kể cả khi là các đơn khác nhau.
    queries.lock_premium_user(db, o.user_id)
    if aware(o.expires_at) <= now():
        queries.expire_pending_order(db, o)
        db.commit()
        raise HTTPException(409, "Đơn đã hết hạn. Vui lòng tạo đơn mới")
    amount = body.amount if body.amount is not None else o.amount
    result = handle_webhook(
        db,
        {
            # Mã giao dịch cố định theo (đơn, số tiền): bấm lại không ghi nhận giao dịch lần hai.
            "id": f"DEMO-{o.id}-{amount}",
            "gateway": settings.sepay_bank,
            "accountNumber": settings.sepay_account,
            "content": f"{o.order_code} thanh toan goi",
            "transferType": "in",
            "transferAmount": amount,
            "referenceCode": "DEMO",
            "source": "demo",
            "description": "Giả lập SePay (chế độ demo)",
        },
    )
    db.refresh(o)
    return {**order_detail(o), "webhook_status": result["status"]}


def cancel_order(*, order_id: int, user: User, db: Session):
    o = queries.get_order_for_cancel(db, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn")
    if o.status != "PENDING":
        raise HTTPException(409, "Chỉ hủy được đơn đang chờ thanh toán")
    o.status = "CANCELLED"
    db.commit()
    return order_out(o)


def refund(*, order_id: int, body: RefundIn, user: User, db: Session):
    o = queries.get_order_for_refund(db, order_id)
    if not o:
        raise HTTPException(404, "Không tìm thấy đơn")
    r = request_refund(db, user, o, body.reason)
    db.commit()
    db.refresh(o)
    return order_out(o, r)


async def sepay_webhook(*, request: Request, authorization: str | None = None, db: Session):
    """SePay gọi khi có tiền vào tài khoản. Header: 'Authorization: Apikey <key>'."""
    if (authorization or "").replace("Apikey", "").strip() != settings.sepay_webhook_key:
        raise HTTPException(401, "Sai API key webhook")
    return handle_webhook(db, await request.json())


def simulate(*, body: SimulateIn, user: User, db: Session):
    """Giả lập SePay chuyển khoản thành công (chỉ bật khi dev) - đi đúng qua hàm xử lý webhook thật."""
    if not settings.enable_dev_tools:
        raise HTTPException(404, "Not found")
    o = queries.get_order_for_simulation(db, body)
    if not o or (o.user_id != user.id and user.role != "ADMIN"):
        raise HTTPException(404, "Không tìm thấy đơn")
    payload = {
        "id": body.tx_id or f"SIM{uuid.uuid4().hex[:10]}",
        "gateway": settings.sepay_bank,
        "transactionDate": "",
        "accountNumber": settings.sepay_account,
        "code": None,
        "content": f"CK {o.order_code} thanh toan goi",
        "transferType": "in",
        "transferAmount": body.amount if body.amount is not None else o.amount,
        "referenceCode": "SIMULATED",
        "description": "Giả lập",
    }
    return {"payload": payload, "result": handle_webhook(db, payload)}
