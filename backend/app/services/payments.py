"""Thanh toán QR/VietQR qua SePay: tạo đơn, webhook idempotent, hết hạn, đối soát, hoàn tiền."""

import logging
import re
from datetime import timedelta, timezone
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Order, Package, PaymentTransaction, Refund, Subscription, User
from ..repositories import payments as queries
from .common import audit, aware, notify, now

log = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))
CODE_RE = re.compile(f"{re.escape(settings.order_prefix)}(\\d+)\\b", re.IGNORECASE)


def qr_url(order: Order) -> str:
    return f"https://qr.sepay.vn/img?acc={quote(settings.sepay_account)}&bank={quote(settings.sepay_bank)}&amount={order.amount}&des={quote(order.order_code or '')}"


def create_order(db: Session, user: User, package: Package) -> Order:
    if not package.active:
        raise HTTPException(400, "Gói dịch vụ đã ngừng bán")
    if package.target != user.role:
        raise HTTPException(403, "Gói này không dành cho loại tài khoản của bạn")
    existing = queries.find_pending(db, package, user)
    if existing:
        return existing
    order = Order(
        user_id=user.id,
        package_id=package.id,
        amount=package.price,
        expires_at=now() + timedelta(minutes=settings.order_expire_minutes),
    )
    queries.add_order(db, order)
    db.flush()
    order.order_code = f"{settings.order_prefix}{order.id:06d}"
    audit(db, user, "ORDER_CREATED", "order", order.id, {"package": package.code, "amount": package.price})
    return order


def activate(db: Session, order: Order):
    pkg = order.package
    start = now()
    if pkg.target == "CANDIDATE":
        user = order.user
        base = aware(user.premium_until) if user.premium_until and aware(user.premium_until) > start else start
        user.premium_until = base + timedelta(days=pkg.duration_days)
        start = base
    queries.add_subscription(db, order, pkg, timedelta(days=pkg.duration_days), start)
    notify(db, order.user_id, "PAYMENT", f"Thanh toán thành công đơn {order.order_code} - {pkg.name}", "/orders")


def handle_webhook(db: Session, payload: dict) -> dict:
    """Xử lý webhook SePay. Idempotent theo mã giao dịch SePay (UNIQUE sepay_tx_id)."""
    tx_id = str(payload.get("id") or payload.get("referenceCode") or "")
    if not tx_id:
        raise HTTPException(400, "Thiếu mã giao dịch")
    if payload.get("transferType", "in") != "in":
        return {"success": True, "status": "IGNORED_OUTGOING"}
    try:
        amount = int(payload.get("transferAmount") or 0)
    except (ValueError, TypeError):
        raise HTTPException(400, "Số tiền giao dịch không hợp lệ")
    if amount <= 0:
        raise HTTPException(400, "Số tiền giao dịch phải lớn hơn 0")
    content = f"{payload.get('content') or ''} {payload.get('code') or ''} {payload.get('description') or ''}"
    tx = PaymentTransaction(
        sepay_tx_id=tx_id, amount=amount, content=content.strip(), status="UNMATCHED", raw_payload=payload
    )
    queries.add_transaction(db, tx)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"success": True, "status": "DUPLICATE"}
    m = CODE_RE.search(content)
    order = queries.lock_order(db, m) if m else None
    if not order or m.group(0).upper() != (order.order_code or "").upper():
        audit(db, None, "PAYMENT_UNMATCHED", "payment_transaction", tx.id, {"content": content})
        db.commit()
        return {"success": True, "status": "UNMATCHED"}
    tx.order_id = order.id
    if amount != order.amount:
        tx.status = "AMOUNT_MISMATCH"
    elif order.status in ("PENDING", "RECONCILING") and aware(order.expires_at) > now():
        res = queries.mark_paid(db, order)
        if res.rowcount == 1:
            db.refresh(order)
            activate(db, order)
            tx.status = "MATCHED"
        else:
            tx.status = "LATE"
    else:
        tx.status = "LATE"
    if tx.status != "MATCHED" and queries.mark_reconciling(db, order).rowcount == 1:
        # Có tiền vào nhưng sai số tiền hoặc đến sau hạn: đơn chờ quản trị viên đối soát (bảng 4.31).
        db.refresh(order)
        notify(db, order.user_id, "PAYMENT", f"Đơn {order.order_code} đang chờ đối soát giao dịch", "/orders")
    audit(db, None, f"PAYMENT_{tx.status}", "order", order.id, {"tx": tx_id, "amount": amount})
    db.commit()
    return {"success": True, "status": tx.status}


def resolve_order(db: Session, admin: User, order: Order, approve: bool, note: str | None):
    """Quản trị viên kết luận đơn RECONCILING: chấp nhận (PAID + kích hoạt) hoặc từ chối (hủy, cần hoàn tiền)."""
    if order.status != "RECONCILING":
        raise HTTPException(409, "Đơn không ở trạng thái chờ đối soát")
    txs = queries.open_transactions_for_order(db, order)
    if approve:
        if not txs:
            raise HTTPException(409, "Chưa có giao dịch nào gắn với đơn này")
        if queries.mark_paid(db, order).rowcount != 1:
            raise HTTPException(409, "Trạng thái đơn đã thay đổi")
        db.refresh(order)
        activate(db, order)
        for t in txs:
            t.status = "RESOLVED"
    else:
        order.status = "CANCELLED"
        for t in txs:
            t.status = "REFUND_DUE"
        notify(db, order.user_id, "PAYMENT", f"Đơn {order.order_code} không được chấp nhận sau đối soát", "/orders")
    audit(
        db,
        admin,
        "ORDER_RECONCILE_" + ("APPROVED" if approve else "REJECTED"),
        "order",
        order.id,
        {"note": note, "transactions": [t.sepay_tx_id for t in txs]},
    )


def assign_transaction(db: Session, admin: User, tx: PaymentTransaction, order: Order):
    """Gắn giao dịch không khớp mã (khách ghi sai nội dung) vào đơn rồi đưa đơn sang chờ đối soát."""
    if tx.status != "UNMATCHED" or tx.order_id:
        raise HTTPException(409, "Chỉ gắn được giao dịch chưa khớp đơn")
    if order.status not in ("PENDING", "EXPIRED", "RECONCILING"):
        raise HTTPException(409, "Đơn đã được xử lý")
    tx.order_id, tx.status = (order.id, "AMOUNT_MISMATCH" if tx.amount != order.amount else "LATE")
    if order.status != "RECONCILING":
        queries.mark_reconciling(db, order)
        db.refresh(order)
    audit(db, admin, "TX_ASSIGNED", "payment_transaction", tx.id, {"order": order.order_code})


def fetch_sepay_transactions(since) -> list[dict]:
    """Lấy lịch sử giao dịch tiền vào từ API SePay, chuyển về cùng định dạng payload webhook."""
    response = httpx.get(
        settings.sepay_api_url,
        params={
            "account_number": settings.sepay_account,
            "transaction_date_min": since.astimezone(VN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "limit": 5000,
        },
        headers={"Authorization": f"Bearer {settings.sepay_api_token}"},
        timeout=30,
    )
    response.raise_for_status()
    out = []
    for t in response.json().get("transactions") or []:
        amount_in = int(float(t.get("amount_in") or 0))
        if amount_in <= 0:
            continue
        out.append(
            {
                "id": str(t.get("id")),
                "transferType": "in",
                "transferAmount": amount_in,
                "content": t.get("transaction_content") or "",
                "code": t.get("code"),
                "referenceCode": t.get("reference_number"),
                "transactionDate": t.get("transaction_date"),
                "source": "sepay_api",
            }
        )
    return out


def sync_with_sepay(db: Session, days: int = 2) -> dict:
    """BR-18: đối chiếu với dữ liệu SePay; giao dịch có ở SePay nhưng thiếu webhook được ghi nhận bổ sung."""
    if not settings.sepay_api_token:
        return {"enabled": False, "missing": []}
    try:
        remote = fetch_sepay_transactions(now() - timedelta(days=days))
    except Exception as exc:
        log.exception("Không lấy được giao dịch từ SePay")
        return {"enabled": True, "error": str(exc), "missing": []}
    known = queries.known_transaction_ids(db, [t["id"] for t in remote]) if remote else set()
    missing = []
    for payload in remote:
        if payload["id"] in known:
            continue
        result = handle_webhook(db, payload)
        missing.append({"tx_id": payload["id"], "amount": payload["transferAmount"], "status": result["status"]})
    return {"enabled": True, "checked": len(remote), "missing": missing}


def expire_orders(db: Session) -> int:
    res = queries.expire_pending(db)
    db.commit()
    return res.rowcount


def reconcile(db: Session) -> dict:
    """Đối soát: đơn PAID phải có đúng 1 giao dịch MATCHED cùng số tiền; liệt kê giao dịch lạc."""
    sepay = sync_with_sepay(db)
    paid = queries.paid_orders(db)
    matched = {t.order_id: t for t in queries.matched_transactions(db)}
    problems = [{"type": "MISSING_WEBHOOK", **m} for m in sepay.get("missing", [])]
    for o in paid:
        t = matched.get(o.id)
        if not t:
            problems.append({"type": "PAID_WITHOUT_TX", "order_code": o.order_code, "amount": o.amount})
        elif t.status == "MATCHED" and t.amount != o.amount:
            problems.append(
                {"type": "AMOUNT_DIFF", "order_code": o.order_code, "order_amount": o.amount, "tx_amount": t.amount}
            )
    stray = queries.unmatched_transactions(db)
    for t in stray:
        problems.append(
            {
                "type": f"TX_{t.status}",
                "tx_id": t.sepay_tx_id,
                "amount": t.amount,
                "content": t.content,
                "received_at": t.received_at.isoformat(),
            }
        )
    total_in = queries.total_received(db) or 0
    total_paid = sum((o.amount for o in paid if o.status != "REFUNDED"))
    total_refunded = sum((o.amount for o in paid if o.status == "REFUNDED"))
    stuck = queries.stuck_orders(db) or 0
    return {
        "checked_at": now().isoformat(),
        "total_received": int(total_in),
        "total_paid_orders": total_paid,
        "total_refunded": total_refunded,
        "stuck_pending_orders": stuck,
        "reconciling_orders": queries.reconciling_count(db) or 0,
        "sepay": {k: v for k, v in sepay.items() if k != "missing"},
        "problems": problems,
    }


def request_refund(db: Session, user: User, order: Order, reason: str) -> Refund:
    if order.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy đơn")
    if order.status != "PAID":
        raise HTTPException(409, "Chỉ yêu cầu hoàn tiền cho đơn đã thanh toán")
    if aware(order.paid_at) < now() - timedelta(days=settings.refund_window_days):
        raise HTTPException(409, f"Đã quá {settings.refund_window_days} ngày kể từ khi thanh toán")
    sub = queries.subscription_for_refund(db, order)
    if sub and order.package.quota_jobs and (sub.remaining_quota < order.package.quota_jobs):
        raise HTTPException(409, "Gói đã được sử dụng để đăng tin nên không thể hoàn tiền")
    res = queries.request_refund(db, order)
    if res.rowcount != 1:
        raise HTTPException(409, "Trạng thái đơn đã thay đổi")
    refund = Refund(order_id=order.id, reason=reason)
    queries.add_refund(db, refund)
    audit(db, user, "REFUND_REQUESTED", "order", order.id, {"reason": reason})
    return refund


def process_refund(db: Session, admin: User, refund: Refund, approve: bool, note: str | None):
    order = refund.order
    if refund.status != "REQUESTED" or order.status != "REFUND_REQUESTED":
        raise HTTPException(409, "Yêu cầu đã được xử lý")
    refund.processed_by, refund.processed_at, refund.admin_note = (admin.id, now(), note)
    if approve:
        refund.status, order.status = ("DONE", "REFUNDED")
        sub = queries.subscription_for_reversal(db, order)
        if sub:
            sub.active = False
            if order.package.target == "CANDIDATE":
                u = order.user
                if u.premium_until:
                    u.premium_until = aware(u.premium_until) - timedelta(days=order.package.duration_days)
        notify(db, order.user_id, "REFUND", f"Đã hoàn tiền đơn {order.order_code}", "/orders")
    else:
        refund.status, order.status = ("REJECTED", "PAID")
        notify(db, order.user_id, "REFUND", f"Yêu cầu hoàn tiền đơn {order.order_code} bị từ chối", "/orders")
    audit(db, admin, "REFUND_" + ("APPROVED" if approve else "REJECTED"), "order", order.id, {"note": note})


def active_hr_subscription(db: Session, user_id: int) -> Subscription | None:
    return queries.active_hr_subscription(db, user_id)
