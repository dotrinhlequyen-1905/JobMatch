from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user
from ...models import User
from ...schemas.payments import DemoPaymentIn, OrderIn, RefundIn, SimulateIn
from ...services import payment_api as payment_api_service
from ...services import payment_api as payments_service

router = APIRouter(prefix="", tags=["payments"])


@router.get("/packages")
def packages(target: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payment_api_service.packages(target=target, db=db)


@router.post("/orders")
def new_order(body: OrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.new_order(body=body, user=user, db=db)


@router.get("/orders")
def my_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.my_orders(user=user, db=db)


@router.post("/dev/simulate-payment")
def simulate(body: SimulateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.simulate(body=body, user=user, db=db)


@router.get("/orders/{order_id}")
def get_order(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.get_order(order_id=order_id, user=user, db=db)


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.cancel_order(order_id=order_id, user=user, db=db)


@router.post("/orders/{order_id}/demo-payment")
def demo_payment(
    order_id: int, body: DemoPaymentIn | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return payments_service.demo_payment(order_id=order_id, body=body or DemoPaymentIn(), user=user, db=db)


@router.post("/orders/{order_id}/refund")
def refund(order_id: int, body: RefundIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return payments_service.refund(order_id=order_id, body=body, user=user, db=db)
