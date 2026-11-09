from datetime import datetime

from pydantic import BaseModel


class HoldIn(BaseModel):
    application_id: int


class SlotsIn(BaseModel):
    start_at: datetime
    end_at: datetime
    minutes: int = 30
    location: str | None = None


class CancelIn(BaseModel):
    reason: str | None = None


class ResultIn(BaseModel):
    result: str
    feedback: str | None = None
