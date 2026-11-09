from typing import Literal

from pydantic import BaseModel, Field


class ReportIn(BaseModel):
    target_type: Literal["JOB", "COMPANY", "USER"]
    target_id: int
    reason: str = Field(min_length=10, max_length=2000)


class ReportDecision(BaseModel):
    status: Literal["RESOLVED", "DISMISSED"]
    note: str | None = None
    # Biện pháp kèm theo khi xác nhận vi phạm
    action: Literal["NONE", "CLOSE_JOB", "LOCK_USER"] = "NONE"
