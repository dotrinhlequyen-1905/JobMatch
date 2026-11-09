from pydantic import BaseModel, Field


class StatusIn(BaseModel):
    status: str
    note: str | None = None


class PackageIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern="^[A-Z0-9_]+$")
    name: str = Field(min_length=2)
    target: str = Field(pattern="^(HR|CANDIDATE)$")
    price: int = Field(ge=1000)
    duration_days: int = Field(ge=1, le=365)
    quota_jobs: int = Field(default=0, ge=0)
    description: str | None = None
    active: bool = True


class AssignIn(BaseModel):
    order_code: str = Field(min_length=3, max_length=40)


class RefundDecision(BaseModel):
    approve: bool
    note: str | None = None
