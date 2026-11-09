from pydantic import BaseModel, Field


class OrderIn(BaseModel):
    package_id: int


class RefundIn(BaseModel):
    reason: str


class DemoPaymentIn(BaseModel):
    # Để trống: chuyển đúng số tiền của đơn; khác số tiền đơn: minh họa giao dịch lệch -> "Chờ đối soát".
    amount: int | None = Field(default=None, gt=0)


class SimulateIn(BaseModel):
    order_id: int
    amount: int | None = None
    tx_id: str | None = None
